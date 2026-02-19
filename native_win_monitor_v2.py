import psutil
import ctypes
from ctypes import wintypes
import os
from typing import Optional, Dict, List, Tuple

ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_void_p)
DEBUG_PDH = os.environ.get("DEBUG_PDH", "").strip().lower() in ("1", "true", "yes")

PDH_FMT_DOUBLE = 0x00000200
PDH_FMT_LARGE  = 0x00000400
PDH_MORE_DATA  = 0x800007D2  # PDH_MORE_DATA

def _hex(code: int) -> str:
    return f"0x{int(code) & 0xFFFFFFFF:08X}"

# ---------------- Kernel: GetPerformanceInfo ----------------
class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", wintypes.DWORD),
        ("ProcessCount", wintypes.DWORD),
        ("ThreadCount", wintypes.DWORD),
    ]

def get_perf_info() -> PERFORMANCE_INFORMATION:
    perf_info = PERFORMANCE_INFORMATION()
    perf_info.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
    ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(perf_info), perf_info.cb)
    return perf_info

# ---------------- PDH structs ----------------
class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]

class PDH_FMT_COUNTERVALUE_LARGE(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("largeValue", ctypes.c_longlong)]

class PdhCounters:
    """
    Robust PDH wrapper.

    FIXES:
      - avoids ctypes argtypes clobbering (PdhGetFormattedCounterValue is ONE function; we use a generic signature)
      - tries both local and machine-qualified paths (\\\\COMPUTER\\Object\\Counter)
      - wildcard expand Paging File(*)% Usage and prefer _Total if present
    """
    def __init__(self):
        self._ok = False
        self._q = wintypes.HANDLE()

        self._c_page_faults = wintypes.HANDLE()
        self._c_pages_sec   = wintypes.HANDLE()
        self._c_page_reads  = wintypes.HANDLE()
        self._c_comp_size   = wintypes.HANDLE()
        self._c_avail_bytes = wintypes.HANDLE()
        self._c_pf_usage    = wintypes.HANDLE()

        self._add_status: Dict[str, int] = {}
        self._chosen_paths: Dict[str, str] = {}
        self._read_status: Dict[str, int] = {}

        try:
            self._pdh = ctypes.WinDLL("pdh.dll")
        except Exception:
            return

        # Open query
        self._open = self._pdh.PdhOpenQueryW
        self._open.argtypes = [wintypes.LPCWSTR, ULONG_PTR, ctypes.POINTER(wintypes.HANDLE)]
        self._open.restype = wintypes.DWORD

        # Add counter (prefer English if available)
        add_eng = getattr(self._pdh, "PdhAddEnglishCounterW", None)
        add_std = getattr(self._pdh, "PdhAddCounterW", None)
        if add_eng is None and add_std is None:
            return
        self._add = add_eng if add_eng is not None else add_std
        self._add.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, ULONG_PTR, ctypes.POINTER(wintypes.HANDLE)]
        self._add.restype = wintypes.DWORD
        self._using_english = add_eng is not None

        # Collect data
        self._collect = self._pdh.PdhCollectQueryData
        self._collect.argtypes = [wintypes.HANDLE]
        self._collect.restype = wintypes.DWORD

        # IMPORTANT: One generic signature for GetFormattedCounterValue to avoid argtypes clobbering
        self._get_fmt = self._pdh.PdhGetFormattedCounterValue
        self._get_fmt.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        self._get_fmt.restype = wintypes.DWORD

        # Expand wildcard paths
        self._expand = self._pdh.PdhExpandWildCardPathW
        self._expand.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
        self._expand.restype = wintypes.DWORD

        st = self._open(None, 0, ctypes.byref(self._q))
        self._add_status["PdhOpenQueryW"] = int(st)
        if st != 0:
            return

        machine = os.environ.get("COMPUTERNAME", "").strip()
        prefix = f"\\\\{machine}" if machine else ""

        def both(path: str) -> List[str]:
            cands = [path]
            if prefix:
                cands.append(prefix + path)
            return cands

        # Add memory counters
        self._add_counter_multi("page_faults", both(r"\Memory\Page Faults/sec"), self._c_page_faults)
        self._add_counter_multi("pages_sec",   both(r"\Memory\Pages/sec"),      self._c_pages_sec)
        self._add_counter_multi("page_reads",  both(r"\Memory\Page Reads/sec"), self._c_page_reads)
        self._add_counter_multi("comp_size",   both(r"\Memory\Compressed Page Size"), self._c_comp_size)
        self._add_counter_multi("avail_bytes", both(r"\Memory\Available Bytes"), self._c_avail_bytes)

        # Paging file % usage: wildcard expand actual instances
        pf_path = self._pick_paging_file_path(prefix)
        if pf_path:
            self._add_counter_multi("pf_usage", [pf_path], self._c_pf_usage)
        else:
            self._add_counter_multi("pf_usage", both(r"\Paging File(_Total)\% Usage"), self._c_pf_usage)

        # Prime once
        try:
            self._collect(self._q)
            self._ok = True
        except Exception:
            self._ok = False

        if DEBUG_PDH:
            print("[PDH DEBUG] using PdhAddEnglishCounterW =", self._using_english)
            print("[PDH DEBUG] chosen paths:")
            for k, p in self._chosen_paths.items():
                print(f"  - {k}: {p}")
            print("[PDH DEBUG] add statuses:")
            for k, v in self._add_status.items():
                print(f"  - {k}: {_hex(v)}")

    def _add_counter_multi(self, name: str, candidates: List[str], out_handle: wintypes.HANDLE):
        for p in candidates:
            h = wintypes.HANDLE()
            st = self._add(self._q, p, 0, ctypes.byref(h))
            self._add_status[p] = int(st)
            if st == 0:
                out_handle.value = h.value
                self._chosen_paths[name] = p
                return

    def _pick_paging_file_path(self, prefix: str) -> Optional[str]:
        for pat in [r"\Paging File(*)\% Usage", (prefix + r"\Paging File(*)\% Usage") if prefix else None]:
            if not pat:
                continue
            size = wintypes.DWORD(0)
            st = self._expand(None, pat, None, ctypes.byref(size), 0)
            self._add_status[f"expand1:{pat}"] = int(st)
            if st not in (PDH_MORE_DATA, 0) or size.value == 0:
                continue
            buf = ctypes.create_unicode_buffer(size.value)
            st2 = self._expand(None, pat, buf, ctypes.byref(size), 0)
            self._add_status[f"expand2:{pat}"] = int(st2)
            if st2 != 0:
                continue
            raw = buf[:]
            paths = [s for s in raw.split("\x00") if s]
            if not paths:
                continue
            for p in paths:
                if r"Paging File(_Total)" in p:
                    return p
            return paths[0]
        return None

    @property
    def ok(self) -> bool:
        return self._ok

    def sample(self):
        if not self._ok:
            return
        try:
            self._collect(self._q)
        except Exception:
            pass

    def _read_double(self, h: wintypes.HANDLE, key: str) -> Optional[float]:
        if not self._ok or not h.value:
            return None
        typ = wintypes.DWORD()
        val = PDH_FMT_COUNTERVALUE()
        st = self._get_fmt(h, PDH_FMT_DOUBLE, ctypes.byref(typ), ctypes.byref(val))
        self._read_status[key] = int(st)
        if st == 0:
            return float(val.doubleValue)
        return None

    def _read_large(self, h: wintypes.HANDLE, key: str) -> Optional[int]:
        if not self._ok or not h.value:
            return None
        typ = wintypes.DWORD()
        val = PDH_FMT_COUNTERVALUE_LARGE()
        st = self._get_fmt(h, PDH_FMT_LARGE, ctypes.byref(typ), ctypes.byref(val))
        self._read_status[key] = int(st)
        if st == 0:
            return int(val.largeValue)
        return None

    def page_faults_per_sec(self) -> Optional[float]:
        return self._read_double(self._c_page_faults, "page_faults")

    def pages_per_sec(self) -> Optional[float]:
        return self._read_double(self._c_pages_sec, "pages_sec")

    def page_reads_per_sec(self) -> Optional[float]:
        return self._read_double(self._c_page_reads, "page_reads")

    def compressed_page_size_bytes(self) -> Optional[int]:
        return self._read_large(self._c_comp_size, "comp_size")

    def available_bytes(self) -> Optional[int]:
        return self._read_large(self._c_avail_bytes, "avail_bytes")

    def paging_file_percent_usage(self) -> Optional[float]:
        return self._read_double(self._c_pf_usage, "pf_usage")

# ---------------- Formatting helpers ----------------
def format_bytes(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

def format_freq_mhz(mhz: Optional[float]) -> str:
    if mhz is None:
        return "n/a"
    if mhz >= 1000:
        return f"{mhz/1000:.2f}GHz"
    return f"{mhz:.0f}MHz"

def format_freq_pair(cur_mhz: Optional[float], max_mhz: Optional[float]) -> str:
    if cur_mhz is None or max_mhz is None or max_mhz <= 0:
        return f"{format_freq_mhz(cur_mhz)}"
    pct = int(round((cur_mhz / max_mhz) * 100))
    return f"{format_freq_mhz(cur_mhz)}/{format_freq_mhz(max_mhz)} {pct:>3}%"

def safe_cpu_freq_percpu():
    try:
        freqs = psutil.cpu_freq(percpu=True)
        if freqs is None:
            return None
        if isinstance(freqs, list):
            return freqs
        logical = psutil.cpu_count() or 1
        return [freqs for _ in range(logical)]
    except Exception:
        return None

def fmt_rate(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:,.1f}"

# ---------------- Process tops ----------------
def prime_process_cpu_counters():
    for p in psutil.process_iter(attrs=["pid"]):
        try:
            p.cpu_percent(interval=None)
        except Exception:
            pass

def top_processes(n: int = 5) -> Tuple[List[Tuple[float, int, str]], List[Tuple[int, int, str, float]]]:
    top_cpu: List[Tuple[float, int, str]] = []
    top_mem: List[Tuple[int, int, str, float]] = []
    for p in psutil.process_iter(attrs=["pid", "name"]):
        try:
            pid = p.info["pid"]
            name = p.info.get("name") or "?"
            cpu = p.cpu_percent(interval=None) or 0.0
            rss = int(p.memory_info().rss)
            mp = float(p.memory_percent())
            top_cpu.append((cpu, pid, name))
            top_mem.append((rss, pid, name, mp))
        except Exception:
            continue
    top_cpu.sort(reverse=True, key=lambda x: x[0])
    top_mem.sort(reverse=True, key=lambda x: x[0])
    return top_cpu[:n], top_mem[:n]

# ---------------- Dashboard ----------------
def draw_monitor():
    logical_cores = psutil.cpu_count() or 1
    physical_cores = psutil.cpu_count(logical=False) or 0

    pdh = PdhCounters()
    prime_process_cpu_counters()

    try:
        while True:
            prime_process_cpu_counters()
            if pdh.ok:
                pdh.sample()

            per_cpu = psutil.cpu_percent(interval=1, percpu=True) or [0.0] * logical_cores
            avg_cpu = sum(per_cpu) / len(per_cpu)
            per_freq = safe_cpu_freq_percpu()

            if pdh.ok:
                pdh.sample()

            pf_s = pdh.page_faults_per_sec() if pdh.ok else None
            pages_s = pdh.pages_per_sec() if pdh.ok else None
            preads_s = pdh.page_reads_per_sec() if pdh.ok else None
            comp_bytes = pdh.compressed_page_size_bytes() if pdh.ok else None
            avail_bytes = pdh.available_bytes() if pdh.ok else None
            pf_usage = pdh.paging_file_percent_usage() if pdh.ok else None

            perf = get_perf_info()
            pg = perf.PageSize

            try:
                swap = psutil.swap_memory()
            except Exception:
                swap = None

            top_cpu, top_mem = top_processes(n=5)

            os.system("cls" if os.name == "nt" else "clear")
            print("=" * 118)
            core_hdr = f" CORES: {physical_cores}P / {logical_cores}L " if physical_cores else f" CORES: {logical_cores}L "
            print(f" ULTIMATE ROBUST MONITOR |{core_hdr}")
            print("=" * 118)

            bar_total = "█" * int(avg_cpu / 4)
            print(f"OVERALL CPU:   [{bar_total:<25}] {avg_cpu:>6.1f}%")

            if per_freq:
                cur_vals = [getattr(f, "current", None) for f in per_freq if f is not None]
                max_vals = [getattr(f, "max", None) for f in per_freq if f is not None]
                cur_vals = [c for c in cur_vals if isinstance(c, (int, float)) and c > 0]
                max_vals = [m for m in max_vals if isinstance(m, (int, float)) and m > 0]
                if cur_vals:
                    cur_avg = sum(cur_vals) / len(cur_vals)
                    if max_vals:
                        max_avg = sum(max_vals) / len(max_vals)
                        pct = int(round((cur_avg / max_avg) * 100)) if max_avg > 0 else 0
                        print(f"CPU SPEED:     {format_freq_mhz(cur_avg)} avg (max ~{format_freq_mhz(max_avg)} avg)  {pct}%")
                    else:
                        print(f"CPU SPEED:     {format_freq_mhz(cur_avg)} avg")

            print(
                "MEM PRESSURE:  "
                f"Page Faults/sec: {fmt_rate(pf_s)} | Pages/sec: {fmt_rate(pages_s)} | Page Reads/sec: {fmt_rate(preads_s)} | "
                f"Compressed: {('n/a' if comp_bytes is None else format_bytes(float(comp_bytes)))}"
            )
            print(
                "MEM AVAIL:     "
                f"Avail Bytes: {('n/a' if avail_bytes is None else format_bytes(float(avail_bytes)))} | "
                f"PagingFile %Usage: {('n/a' if pf_usage is None else f'{pf_usage:,.1f}%')}"
            )

            if DEBUG_PDH and pdh.ok:
                print("\n[PDH DEBUG] chosen paths:")
                for k, p in pdh._chosen_paths.items():
                    print(f"  - {k}: {p}")
                print("[PDH DEBUG] last read statuses:")
                for k, v in pdh._read_status.items():
                    print(f"  - {k}: {_hex(v)}")

            print("-" * 118)
            print("PER-CORE UTILIZATION + SPEED:")
            n = len(per_cpu)
            half = (n + 1) // 2
            for i in range(half):
                left_val = per_cpu[i]
                l_bar = "■" * int(left_val / 10)
                l_speed = "n/a"
                if per_freq and i < len(per_freq) and per_freq[i] is not None:
                    l_speed = format_freq_pair(getattr(per_freq[i], "current", None), getattr(per_freq[i], "max", None))

                right_idx = i + half
                if right_idx < n:
                    right_val = per_cpu[right_idx]
                    r_bar = "■" * int(right_val / 10)
                    r_speed = "n/a"
                    if per_freq and right_idx < len(per_freq) and per_freq[right_idx] is not None:
                        r_speed = format_freq_pair(getattr(per_freq[right_idx], "current", None), getattr(per_freq[right_idx], "max", None))

                    print(
                        f" Core {i:02}: [{l_bar:<10}] {left_val:>5.1f}% {l_speed:<18} |"
                        f" Core {right_idx:02}: [{r_bar:<10}] {right_val:>5.1f}% {r_speed:<18}"
                    )
                else:
                    print(f" Core {i:02}: [{l_bar:<10}] {left_val:>5.1f}% {l_speed:<18}")

            print("\n" + "=" * 118)
            print("DEEP MEMORY BLOCKS (KERNEL & SYSTEM):")
            print(f" Physical Total:     {format_bytes(perf.PhysicalTotal * pg):>18}")
            print(f" Physical Available: {format_bytes(perf.PhysicalAvailable * pg):>18}")
            print(f" Commit Total:       {format_bytes(perf.CommitTotal * pg):>18} (Current Load)")
            print(f" Commit Limit:       {format_bytes(perf.CommitLimit * pg):>18} (RAM + Pagefile)")
            print("-" * 118)
            print(f" Kernel Paged:       {format_bytes(perf.KernelPaged * pg):>18} (Swappable)")
            print(f" Kernel Non-Paged:   {format_bytes(perf.KernelNonpaged * pg):>18} (Driver Resident)")

            if swap is not None:
                print("-" * 118)
                print("PAGEFILE / SWAP (psutil):")
                print(f" Swap Total:         {format_bytes(swap.total):>18}")
                print(f" Swap Used:          {format_bytes(swap.used):>18} ({swap.percent:>5.1f}%)")
                print(f" Swap Free:          {format_bytes(swap.free):>18}")

            print("\n" + "=" * 118)
            print("TOP PROCESSES:")
            print("  By CPU% (last ~1s):")
            for cpu, pid, name in top_cpu:
                print(f"   - {cpu:>6.1f}%  PID {pid:<7}  {name}")
            print("  By RSS (working set):")
            for rss, pid, name, mp in top_mem:
                print(f"   - {format_bytes(rss):>10}  ({mp:>4.1f}%)  PID {pid:<7}  {name}")

            print("\n" + "=" * 118)
            print(f" Handles: {perf.HandleCount:,} | Processes: {perf.ProcessCount:,} | Threads: {perf.ThreadCount:,}")
            print("=" * 118)
            print("Press Ctrl+C to stop.")

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    draw_monitor()
