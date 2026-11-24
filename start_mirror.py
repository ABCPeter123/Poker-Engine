"""Start a local UxPlay receiver and fit its native window to stream geometry."""
import argparse
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

GEOMETRY = re.compile(r"geometry is \(w,h\)=\((\d+),(\d+)\) \(source\);\s*\(x,y\)=\((\d+),(\d+)\);\s*\(w,h\)=\((\d+),(\d+)\)")

def parse_geometry(line):
    match = GEOMETRY.search(line)
    if not match:
        return None
    w, h, x, y, visible_w, visible_h = map(int, match.groups())
    if 0 < visible_w <= w <= 8192 and 0 < visible_h <= h <= 8192:
        return visible_w, visible_h
    return None

def fit_size(w, h, limit_w, limit_h):
    scale = min(limit_w / w, limit_h / h)
    return max(1, round(w * scale)), max(1, round(h * scale))

def native_window(pid, geometry, max_width):
    """Resize only a visible, unowned top-level window of this UxPlay process."""
    u = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    u.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    u.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    u.GetWindow.restype = wintypes.HWND
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsIconic.argtypes = [wintypes.HWND]
    u.IsZoomed.argtypes = [wintypes.HWND]
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    u.MonitorFromWindow.restype = wintypes.HANDLE
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
    u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    candidates = []
    @callback_type
    def each(hwnd, _):
        owner = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid or not u.IsWindowVisible(hwnd) or u.GetWindow(hwnd, 4) or u.IsIconic(hwnd) or u.IsZoomed(hwnd):
            return True
        client = wintypes.RECT()
        if u.GetClientRect(hwnd, ctypes.byref(client)) and client.right >= 64 and client.bottom >= 64:
            candidates.append((client.right * client.bottom, hwnd))
        return True
    u.EnumWindows(each, 0)
    if not candidates:
        return False
    _, hwnd = max(candidates, key=lambda x: x[0])
    outer, client = wintypes.RECT(), wintypes.RECT()
    if not u.GetWindowRect(hwnd, ctypes.byref(outer)) or not u.GetClientRect(hwnd, ctypes.byref(client)):
        return False
    mon = u.MonitorFromWindow(hwnd, 2)
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(info)
    if not u.GetMonitorInfoW(mon, ctypes.byref(info)):
        return False
    work = info.rcWork
    border_w = max(0, outer.right - outer.left - client.right)
    border_h = max(0, outer.bottom - outer.top - client.bottom)
    aw = max(1, work.right - work.left - border_w)
    ah = max(1, work.bottom - work.top - border_h)
    w, h = fit_size(*geometry, min(aw, max_width), min(ah, round(ah * .8)))
    ow, oh = w + border_w, h + border_h
    x = min(max(outer.left, work.left), work.right - ow)
    y = min(max(outer.top, work.top), work.bottom - oh)
    return bool(u.SetWindowPos(hwnd, None, x, y, ow, oh, 0x0004 | 0x0010))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", default=r"C:\msys64\ucrt64\bin\uxplay.exe")
    parser.add_argument("--max-width", type=int, default=1100)
    parser.add_argument("--software", action="store_true", help="Force software decoding if GPU rotation fails")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This launcher is for Windows.")
    if not 320 <= args.max_width <= 3840:
        parser.error("max-width must be 320–3840")
    exe = Path(args.exe).resolve()
    if not exe.is_file():
        parser.error("UxPlay not found. Supply --exe with the installed executable path.")
    try:
        ctypes.WinDLL("user32").SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass
    env = dict(os.environ)
    env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
    command = [str(exe), "-n", "Private Mirror", "-nh", "-pin",
               "-s", "1920x1080", "-fps", "30", "-vs", "d3d11videosink force-aspect-ratio=true"]
    if args.software:
        command.append("-avdec")
    print("Starting private AirPlay receiver with Apple-style PIN authentication. Enter the current PIN displayed in this terminal when prompted.", flush=True)
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", bufsize=1)
    updates = queue.Queue()
    def read_output():
        for line in process.stdout:
            print(line.rstrip(), flush=True)
            value = parse_geometry(line)
            if value:
                updates.put(value)
    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    geometry = None
    deadline = 0
    fitted = None
    try:
        while process.poll() is None:
            try:
                while True:
                    geometry = updates.get_nowait()
                    fitted = None
                    deadline = time.monotonic() + 8
            except queue.Empty:
                pass
            if geometry and geometry != fitted and time.monotonic() < deadline:
                if native_window(process.pid, geometry, args.max_width):
                    fitted = geometry
                    print(f"Native window fitted to {geometry[0]}:{geometry[1]}", flush=True)
            time.sleep(.2)
    except KeyboardInterrupt:
        print("Stopping AirPlay receiver.", flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        thread.join(timeout=1)
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
