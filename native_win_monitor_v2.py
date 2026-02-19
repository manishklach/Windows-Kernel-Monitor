import psutil
import ctypes
from ctypes import wintypes
import time
import os

# --- Windows Kernel API Setup (Direct System Calls) ---
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

def get_perf_info():
    perf_info = PERFORMANCE_INFORMATION()
    perf_info.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
    ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(perf_info), perf_info.cb)
    return perf_info

def format_bytes(n):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024: return f"{n:.2f} {unit}"
        n /= 1024

# --- Dashboard Logic ---
def draw_monitor():
    logical_cores = psutil.cpu_count()
    physical_cores = psutil.cpu_count(logical=False)
    
    try:
        while True:
            # 1. CPU Section (Using psutil - most robust for per-core data)
            per_cpu = psutil.cpu_percent(interval=1, percpu=True)
            avg_cpu = sum(per_cpu) / len(per_cpu)
            
            # 2. Memory Section (Using Direct Kernel API - avoids WMI/PDH errors)
            perf = get_perf_info()
            pg = perf.PageSize
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print("="*65)
            print(f" ULTIMATE ROBUST MONITOR | CORES: {physical_cores}P / {logical_cores}L ")
            print("="*65)
            
            # Total CPU Bar
            bar_total = "█" * int(avg_cpu / 4)
            print(f"OVERALL CPU:   [{bar_total:<25}] {avg_cpu:>6.1f}%")
            print("-" * 65)
            
            # Per-Core Grid (2 columns for better visibility)
            print("PER-CORE UTILIZATION:")
            half = len(per_cpu) // 2
            for i in range(half):
                left_val = per_cpu[i]
                right_val = per_cpu[i + half]
                l_bar = "■" * int(left_val / 10)
                r_bar = "■" * int(right_val / 10)
                print(f" Core {i:02}: [{l_bar:<10}] {left_val:>5.1f}% | Core {i+half:02}: [{r_bar:<10}] {right_val:>5.1f}%")

            print("\n" + "="*65)
            print("DEEP MEMORY BLOCKS (KERNEL & SYSTEM):")
            print(f" Physical Total:     {format_bytes(perf.PhysicalTotal * pg):>15}")
            print(f" Physical Available: {format_bytes(perf.PhysicalAvailable * pg):>15}")
            print(f" Commit Total:       {format_bytes(perf.CommitTotal * pg):>15} (Current Load)")
            print(f" Commit Limit:       {format_bytes(perf.CommitLimit * pg):>15} (RAM + Swap)")
            print("-" * 65)
            print(f" Kernel Paged:       {format_bytes(perf.KernelPaged * pg):>15} (Swappable)")
            print(f" Kernel Non-Paged:   {format_bytes(perf.KernelNonpaged * pg):>15} (Driver Resident)")
            
            print("\n" + "="*65)
            print(f" Handles: {perf.HandleCount:,} | Processes: {perf.ProcessCount:,} | Threads: {perf.ThreadCount:,}")
            print("="*65)
            print("Press Ctrl+C to stop.")
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    # Ensure psutil is installed: pip install psutil
    draw_monitor()