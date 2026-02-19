# Windows Kernel Monitor (Admin-Friendly) — Native Python

A **single-file**, **no-GUI** Windows performance monitor that prints a high-signal terminal dashboard with **CPU**, **memory pressure**, **paging health**, **pagefile**, **kernel memory**, and **top process** stats.

> **Run as Administrator (recommended / some environments).**  
> Some counters and process details may be limited without elevated privileges.

---

## What’s new (v14)

- **EMA smoothing (10s)** for key memory pressure counters:
  - Page Faults/sec, Pages/sec, Page Reads/sec
- **Paging Health line** with:
  - `HardFaultPressure: OK/WARN/HOT` (heuristic label)
  - `Index: 0–100` (monotonic “hard-fault pressure” indicator)
- **Compressed memory robustness**
  - Tries several PDH compressed-bytes counters
  - Falls back to **MemCompression RSS** (working set) if PDH counter isn’t available

---

## Features

### CPU
- Overall CPU utilization (%)
- Per-core utilization (%)
- CPU frequency (avg + per-core current/max when available)

### Memory pressure (PDH)
- **Page Faults/sec**
- **Pages/sec**
- **Page Reads/sec**
- Each shown as: **instant** + **EMA10** (10-second exponential moving average)

### Paging health (derived)
A quick interpretation layer for “are we actually paging to disk?”:

- **HardFaultPressure**:
  - `OK` — low disk-backed paging
  - `WARN` — noticeable paging I/O
  - `HOT` — sustained high paging I/O
- **Index (0–100)**:
  - dominated by Page Reads/sec, with a smaller contribution from Pages/sec

> This is a heuristic meant to be **useful**, not “scientific”.

### Memory compression (PDH + fallback)
- If available: PDH compressed-bytes counter
- Otherwise: **MemCompression process RSS** shown as:
  - `Compressed: X (MemCompression RSS)`

### Memory availability & pagefile (PDH)
- Memory\\Available Bytes
- Paging File(*)\\% Usage (instance resolved via wildcard expansion, prefers `_Total`)

### Deep kernel/system memory (GetPerformanceInfo)
- Physical Total / Available
- Commit Total / Commit Limit
- Kernel Paged / Kernel Non-Paged
- Handles / Processes / Threads

### Swap / pagefile (psutil)
- Swap Total / Used / Free / %

### Top processes
- Top by CPU% (last ~1s)
- Top by RSS (working set) + % of system memory

---

## Requirements

- Windows 10/11
- Python 3.9+ recommended (3.8+ usually OK)
- `psutil` (only external dependency)

---

## Install

```powershell
python -m pip install --upgrade pip
python -m pip install psutil
```

---

## Run

Open **PowerShell as Administrator** (recommended / some environments) and run:

```powershell
python .\native_win_monitor_v14.py
```

Stop: `Ctrl + C`

---

## Debug PDH counters

If some PDH values show `n/a`:

```powershell
$env:DEBUG_PDH="1"
python .\native_win_monitor_v14.py
```

This prints:
- which exact PDH counter paths were chosen
- PDH status codes for reads

---

## License

MIT License (see below)

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
