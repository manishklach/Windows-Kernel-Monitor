# Ultimate Robust Monitor (Windows)

A lightweight Windows terminal dashboard that displays **CPU + deep memory + kernel + system counters** in real time.

File: `native_win_monitor_v2.py`

---

## What it shows

### CPU
- **Logical cores / Physical cores**
- **Overall CPU** utilization bar + percentage
- **Per-core utilization** in a **2-column grid**

### Deep memory + kernel/system blocks (via Windows `GetPerformanceInfo`)
All memory numbers come from the Windows API and are scaled by `PageSize`.

- **Physical Total**: total RAM usable by the OS
- **Physical Available**: RAM immediately available for allocation
- **Commit Total**: current committed virtual memory (“commit charge”)
- **Commit Limit**: max commit (RAM + pagefile)
- **Kernel Paged**: kernel memory that can be paged out
- **Kernel Non-Paged**: kernel memory that cannot be paged out

### System counters
- **Handles**
- **Processes**
- **Threads**

### Refresh behavior
- Updates about once per second (CPU sampling uses a 1s interval)
- Stop with **Ctrl+C**

---

## Requirements

- Windows 10/11 (or Windows Server)
- Python 3.9+ recommended
- `psutil`

---

## Install

### 1) Install Python
Install Python from python.org and ensure **“Add Python to PATH”** is checked.

Verify:
```powershell
python --version
```

### 2) (Recommended) Create and activate a virtual environment
From the repo folder:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3) Install dependencies
```powershell
pip install --upgrade pip
pip install psutil
```

---

## Run

### Run (standard)
```powershell
python native_win_monitor_v2.py
```

---

## Run as Administrator (recommended / some environments)

Some Windows environments restrict access to certain system counters unless elevated, or you may want consistent access when running under strict enterprise policies.

### Option A (recommended): Start your terminal as Admin
1. Start Menu → search **Windows Terminal** (or **PowerShell**)
2. Right-click → **Run as administrator**
3. `cd` into the repo folder
4. Run:
```powershell
python native_win_monitor_v2.py
```

### Option B: Launch an Admin PowerShell from your current terminal
```powershell
Start-Process powershell -Verb RunAs -ArgumentList "cd '$PWD'; python native_win_monitor_v2.py"
```

---

## Output layout (what you’ll see)

- Header:
  - `ULTIMATE ROBUST MONITOR | CORES: <physical>P / <logical>L`
- CPU:
  - Overall CPU bar `[█████...] xx.x%`
  - Per-core grid in two columns:
    - `Core 00: [■■■■      ]  40.0% | Core 08: [■■■       ]  30.0%`
- Deep memory blocks:
  - Physical + Commit + Kernel paged/non-paged
- System counters:
  - Handles | Processes | Threads
- Footer:
  - `Press Ctrl+C to stop.`

---

## How it works (implementation notes)

- CPU:
  - Uses `psutil.cpu_count()` and `psutil.cpu_count(logical=False)`
  - Uses `psutil.cpu_percent(interval=1, percpu=True)` for per-core utilization  
    (the 1-second interval sets the refresh cadence)

- Memory/kernel/system counters:
  - Uses `ctypes.windll.psapi.GetPerformanceInfo(...)`
  - Reads fields from the `PERFORMANCE_INFORMATION` struct
  - Converts page counts to bytes using `PageSize`
  - Formats values into B/KB/MB/GB/TB

- Screen refresh:
  - Clears terminal with `cls` on Windows before redraw

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'psutil'`
```powershell
pip install psutil
```

### Output looks misaligned
- Use a monospace terminal (Windows Terminal recommended)
- Increase terminal width (the dashboard assumes ~65+ columns)

### Permission / access issues
- Run the terminal **as Administrator** (see above)

---

## License

### Recommended: MIT License
If you want a permissive license, MIT is a common choice.

1) Create a file named `LICENSE` in the repo root  
2) Paste the following text and update the year + name:

```
MIT License

Copyright (c) 2026 <YOUR NAME>

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
```

If you prefer **Apache-2.0** or **GPLv3**, swap this section accordingly.
