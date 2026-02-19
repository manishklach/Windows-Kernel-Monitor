# Windows Kernel Monitor (Admin-Friendly) — Native Python

A **single-file**, **no-GUI** Windows performance monitor that prints a high-signal terminal dashboard with **CPU**, **memory pressure**, **pagefile**, **kernel memory**, and **top process** stats. Designed to be **robust on real Windows boxes** (including mixed PDH availability) and **safe to run continuously**.

> **Run as Administrator (recommended / some environments).**  
> Some counters and process details may be limited without elevated privileges.

---

## Features

### CPU
- **Overall CPU utilization** (%)
- **Per-core utilization** (%)
- **CPU frequency**
  - Average current frequency across cores (from `psutil`)
  - Per-core current/max frequency and % of max (when available)

### Memory pressure (PDH)
- **Page Faults/sec** (`\Memory\Page Faults/sec`)
- **Pages/sec** (`\Memory\Pages/sec`)
- **Page Reads/sec** (`\Memory\Page Reads/sec`)
- **Compressed Page Size** (`\Memory\Compressed Page Size`)  
  (Windows Memory Compression footprint, shown as bytes/MB/GB)

### Memory availability & pagefile (PDH)
- **Memory\Available Bytes** (`\Memory\Available Bytes`)
- **Paging File(_Total)\% Usage** (resolved via wildcard expansion when needed)

### Deep kernel/system memory (GetPerformanceInfo)
- **Physical Total / Available**
- **Commit Total / Commit Limit**
- **Kernel Paged** (swappable)
- **Kernel Non-Paged** (resident)

### Swap / pagefile (psutil)
- **Swap Total / Used / Free / %** (Windows pagefile exposure via `psutil.swap_memory()`)

### Top processes
- **Top by CPU%** (last ~1s window)
- **Top by RSS (Working Set)** with % of system memory

### System totals
- **Handles**, **Processes**, **Threads** (from `GetPerformanceInfo`)

---

## Screenshot

The dashboard is a terminal output updated about once per second, e.g.:

- CPU bars (overall + per-core)
- Memory pressure counters (page faults/pages/page reads)
- Memory compression size
- Paging file usage + available bytes
- Deep kernel memory + swap/pagefile details
- Top processes by CPU + memory

---

## Requirements

- **Windows 10/11**
- **Python 3.9+** recommended (3.8+ usually OK)
- `psutil` (only external dependency)

> PDH is part of Windows. The script uses `ctypes` to call PDH + kernel APIs directly.

---

## Installation

### Option A — pip install dependency
```powershell
python -m pip install --upgrade pip
python -m pip install psutil
```

### Option B — venv (recommended)
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install psutil
```

---

## Usage

### Run (recommended: elevated shell)
Open **PowerShell as Administrator** (recommended / some environments) and run:

```powershell
python .\native_win_monitor_v12.py
```

Stop with:
- `Ctrl + C`

---

## Troubleshooting

### 1) Some values show `n/a`
That usually means:
- A PDH counter could not be bound on this system, or
- You are not running with enough privileges, or
- That metric is not exposed by your Windows build / perf counter set.

Try running as Administrator and/or enable PDH debug:

```powershell
$env:DEBUG_PDH="1"
python .\native_win_monitor_v12.py
```

This prints which exact PDH counter paths were chosen and PDH status codes.

### 2) PDH counter path quirks
Different Windows builds sometimes require the machine-qualified path:
- `\\COMPUTERNAME\Memory\Page Faults/sec`

The script automatically tries both local and machine-qualified forms when applicable.

### 3) Per-core CPU frequency shows `n/a` for some cores
On some systems (especially hybrid CPU topologies / driver combinations), Windows or `psutil` may not expose per-core frequency for every logical core. The monitor will still show overall CPU utilization correctly.

---

## What each metric means (quick guide)

- **Page Faults/sec**: total page faults (soft + hard) per second. Spikes can be normal; sustained high values may indicate memory pressure or heavy paging activity.
- **Pages/sec**: pages read/written to resolve hard faults; often correlates with paging I/O pressure.
- **Page Reads/sec**: reads from disk to resolve hard faults (more directly I/O-related).
- **Compressed Page Size**: amount of memory occupied by Windows’ memory compression store.
- **Available Bytes**: immediately available physical memory for allocation.
- **Paging File % Usage**: percent usage of the pagefile (instance resolved to `_Total` if present).
- **Commit Total / Limit**: committed virtual memory vs commit limit (RAM + pagefile).
- **Kernel Paged / Non-Paged**: kernel memory that can/cannot be paged out.

---

## Files

- `native_win_monitor_v12.py` — main monitor script

---

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
