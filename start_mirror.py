"""Start a local UxPlay receiver and fit its native window to stream geometry."""
import argparse
import getpass
import hashlib
import uuid
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

def parse_sink_geometry(line):
    # Only negotiated sink caps, not advertised capability ranges.
    if "d3d11videosink" not in line.lower() or not re.search(r"set[_ ]caps|updating window with caps", line, re.I):
        return None
    width = re.search(r"\bwidth\s*=\s*(?:\(int\))?\s*(\d+)\b", line)
    height = re.search(r"\bheight\s*=\s*(?:\(int\))?\s*(\d+)\b", line)
    if not width or not height:
        return None
    w, h = int(width[1]), int(height[1])
    if not (64 <= w <= 8192 and 64 <= h <= 8192):
        return None
    par = re.search(r"\bpixel-aspect-ratio\s*=\s*(?:\(fraction\))?\s*(\d+)\s*/\s*(\d+)", line)
    if par and int(par[1]) and int(par[2]):
        w = round(w * int(par[1]) / int(par[2]))
    return (w, h) if 64 <= w <= 8192 else None

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

def receiver_id(node, mode):
    # Stable per computer and authentication mode; not the physical MAC.
    raw = hashlib.sha256(f"poker-engine-mirror-v2:{node}:{mode}".encode()).digest()[:6]
    octets = bytes([(raw[0] & 0xfc) | 0x02]) + raw[1:]
    return ":".join(f"{b:02x}" for b in octets)

def auth_options(mode, password=None):
    if mode == "pin":
        return ["-pin"]
    if mode == "random":
        return ["-pw"]
    if mode != "password" or not password or len(password) < 8 or not password.isascii() or not password.isalnum():
        raise ValueError("Choose a dedicated AirPlay password of at least 8 ASCII letters/digits.")
    return ["-pw", password]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", default=r"C:\msys64\ucrt64\bin\uxplay.exe")
    parser.add_argument("--max-width", type=int, default=1100)
    parser.add_argument("--software", action="store_true", help="Force software decoding if GPU rotation fails")
    parser.add_argument("--landscape", action="store_true", help="Force a wide receiver window (fallback if stream geometry events are missing)")
    parser.add_argument("--auth", choices=("password","random","pin"), default="password",
                        help="Fixed password (default), rotating password, or Apple-style PIN pairing")
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
    # Limit debug output to the renderer whose negotiated dimensions we need.
    env["GST_DEBUG"] = "d3d11videosink:5"
    env["GST_DEBUG_NO_COLOR"] = "1"
    password = getpass.getpass("AirPlay password (reuse the same dedicated password each launch): ") if args.auth == "password" else None
    try:
        auth = auth_options(args.auth, password)
    except ValueError as exc:
        parser.error(str(exc))
    name = "Private Mirror Secure" if args.auth == "password" else "Private Mirror " + args.auth.title()
    command = [str(exe), "-n", name, "-nh", "-m", receiver_id(uuid.getnode(), args.auth), *auth,
               "-s", "1920x1080", "-fps", "30", "-vs", "d3d11videosink force-aspect-ratio=true"]
    if args.software:
        command.append("-avdec")
    print(f"Starting {name}. Select this receiver on your iPhone. Authentication: {args.auth}.", flush=True)
    if args.auth == "password":
        print("Use the dedicated password you just entered if iOS prompts.", flush=True)
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", bufsize=1)
    updates = queue.Queue()
    def read_output():
        for line in process.stdout:
            sink_size = parse_sink_geometry(line)
            value = sink_size or parse_geometry(line)
            if value:
                updates.put(("sink" if sink_size else "airplay", value))
            if not re.search(r"\b(?:DEBUG|LOG|TRACE|MEMDUMP)\b", line):
                print(line.rstrip(), flush=True)
    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()
    geometry = (1536, 709) if args.landscape else None
    deadline = time.monotonic() + 300 if args.landscape else 0
    fitted = None
    last_sink = 0.0
    last_fit_attempt = 0.0
    try:
        while process.poll() is None:
            try:
                while True:
                    kind, value = updates.get_nowait()
                    if args.landscape:
                        continue
                    now = time.monotonic()
                    if kind == "sink":
                        last_sink = now
                    elif last_sink and now - last_sink < 2:
                        continue
                    if value != geometry or fitted is None:
                        geometry = value
                        fitted = None
                        deadline = now + 30
                        print(f"Video geometry ({kind}): {value[0]} x {value[1]}", flush=True)
            except queue.Empty:
                pass
            now = time.monotonic()
            if geometry and geometry != fitted and now < deadline and now - last_fit_attempt >= .35:
                last_fit_attempt = now
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
