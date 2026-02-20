# Windows Kernel Monitor (Native) — Ultimate Robust Monitor

A single-file, dependency-light Windows monitoring tool (Python) focused on **real-time CPU + memory + kernel + paging** visibility, with an **optional GPU block** (via Windows Performance Counters).

This is designed to be run in a terminal and refreshed continuously (like a lightweight `top` for Windows, but with paging + kernel memory focus).

---

## Features

### CPU
- Overall CPU utilization (rolling)
- **Per-core utilization**
- **Per-core effective clock** (GHz) and normalized speed (% of max observed)
- Detects and displays core counts and hybrid/core labeling when available

### Memory (Deep)
- Physical Total / Available
- Commit Total / Commit Limit
- Kernel **Paged** and **Non-Paged** pool
- Swap/Pagefile total/used/free (via `psutil`)

### Paging / Memory Pressure (PDH)
- **Page Faults/sec** (PF/s) + EMA smoothing
- **Pages/sec** + EMA smoothing
- **Page Reads/sec** + EMA smoothing
- **PagingFile(*) % Usage**
- **Memory\Available Bytes**
- Derived **HardFaultPressure index** (0–100) and qualitative label (OK/WARN/HOT)

### Memory Compression
- “Compressed” memory estimate using the **MemCompression** process RSS (working set)

### Processes
- Top processes by CPU%
- Top processes by RSS (working set)
- Handles / processes / threads totals

### GPU (Windows PDH — NEW)
- Overall GPU utilization (aggregated from GPU engine counters)
- Per-engine breakdown (top engine categories), typically:
  - `3D`, `Copy`, `Compute`, `VideoDecode`, `VideoEncode` (others may appear depending on driver)
- GPU adapter memory usage:
  - Dedicated usage
  - Shared usage

Example GPU line:
```
GPU: Util: 2.6% | Engines: 3D:2.6% | Copy:0.2% | ... | Mem: Dedicated 853.36 MB | Shared 661.43 MB
```

---

## Requirements

- Windows 10/11
- Python 3.9+ recommended (3.8+ typically OK)
- No Visual Studio / compilation required

### Python dependencies
Install:
```powershell
python -m pip install --upgrade pip
python -m pip install psutil
```

*(Everything else is standard library: `ctypes`, `time`, `datetime`, etc.)*

---

## Run

### Basic
```powershell
python .\native_win_monitor_v29.py
```

### Run as Administrator (recommended / some environments)
Some counters or process visibility can be restricted on certain systems. If you see `Access is denied` or missing counters, run PowerShell or Windows Terminal **as Administrator**:
```powershell
python .\native_win_monitor_v29.py
```

Stop anytime with **Ctrl+C**.

---

## Output Notes / Interpretation

### Page Faults/sec vs Pages/sec vs Page Reads/sec
- **Page Faults/sec** includes *soft faults* and *hard faults* (not all are disk I/O).
- **Pages/sec** is a stronger indicator of paging activity (potentially hard faults).
- **Page Reads/sec** indicates paging reads from disk and is often the most “painful” when elevated.

### HardFaultPressure Index
A simple heuristic derived from `Page Reads/sec` and `Pages/sec`:
- **OK**: low paging pressure
- **WARN**: noticeable paging activity
- **HOT**: sustained hard faults / disk reads likely impacting responsiveness

### Memory Compression
Windows memory compression isn’t always exposed as a clean global counter. This tool estimates it using the **MemCompression** process working set.

### GPU Block
GPU values come from Windows Performance Counters:
- `\GPU Engine(*)\Utilization Percentage`
- `\GPU Adapter Memory(*)\Dedicated Usage`
- `\GPU Adapter Memory(*)\Shared Usage`

Some drivers expose extra engine categories (e.g., `Security`, `High`). That’s normal.

---

## Troubleshooting

### “n/a” for some PDH counters
Some counters may be missing or named differently on certain Windows builds/locales. The tool already tries multiple counter path variants.

### Verify counters exist with `typeperf`
Examples:
```powershell
typeperf "\Memory\Page Faults/sec" -sc 3
typeperf "\Memory\Pages/sec" -sc 3
typeperf "\Memory\Page Reads/sec" -sc 3
typeperf "\Paging File(*)\% Usage" -sc 3
typeperf "\Memory\Available Bytes" -sc 3
typeperf "\GPU Engine(*)\Utilization Percentage" -sc 3
typeperf "\GPU Adapter Memory(*)\Shared Usage" -sc 3
```

### Missing GPU counters
Some systems (or drivers) may not expose GPU Engine counters. Task Manager may still show GPU usage even if counters are missing.

### Permission issues
Run PowerShell/Terminal **as Administrator** (recommended / some environments).

---

## Repository Layout (suggested)

```
windows-kernel-monitor/
  native_win_monitor_v29.py
  README.md
  LICENSE
```

If you prefer the canonical filename to stay `native_win_monitor.py`, rename:
```powershell
Rename-Item .\native_win_monitor_v29.py native_win_monitor.py
```

---

## License

MIT License. See `LICENSE`.

---

## Contributing
PRs welcome. If you’re adding new counters:
- Prefer **PDH** counters when available (portable and scriptable)
- Keep the terminal output stable and readable (avoid overly wide lines)
- Add a `typeperf` verification line to this README when introducing new counters
