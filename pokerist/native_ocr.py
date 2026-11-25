"""Reuse the installed Tesseract library; fall back to the existing CLI."""
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import io
import subprocess
import atexit

_instances={}
_failed=set()
_dll_dirs=[]

class NativeOCR:
    def __init__(self,exe):
        root=Path(exe).resolve().parent
        if os.name=="nt":
            if hasattr(os,"add_dll_directory"):
                _dll_dirs.append(os.add_dll_directory(str(root)))
            paths=sorted(root.glob("*tesseract*.dll"))
        else:
            found=ctypes.util.find_library("tesseract")
            paths=[found] if found else []
        if not paths:
            raise OSError("Tesseract shared library not found")
        self.lib=None
        for path in paths:
            try:
                lib=C.CDLL(str(path))
                getattr(lib,"TessBaseAPIGetTsvText")
                self.lib=lib
                break
            except (OSError,AttributeError):
                continue
        if self.lib is None:
            raise OSError("No compatible Tesseract shared library")
        p=C.c_void_p; i=C.c_int; s=C.c_char_p
        for name,args,ret in [
            ("TessBaseAPICreate",[],p),("TessBaseAPIDelete",[p],None),
            ("TessBaseAPIInit3",[p,s,s],i),("TessBaseAPISetPageSegMode",[p,i],None),
            ("TessBaseAPISetVariable",[p,s,s],i),
            ("TessBaseAPISetImage",[p,p,i,i,i,i],None),
            ("TessBaseAPISetSourceResolution",[p,i],None),
            ("TessBaseAPIGetTsvText",[p,i],p),("TessDeleteText",[p],None),
            ("TessBaseAPIClear",[p],None),("TessBaseAPIClearAdaptiveClassifier",[p],None)
        ]:
            f=getattr(self.lib,name);f.argtypes=args;f.restype=ret
        self.handle=self.lib.TessBaseAPICreate()
        if not self.handle:
            raise RuntimeError("Could not allocate OCR handle")
        data=os.environ.get("TESSDATA_PREFIX")
        if not data and (root/"tessdata"/"eng.traineddata").is_file():
            data=str(root/"tessdata")
        if self.lib.TessBaseAPIInit3(self.handle,os.fsencode(data) if data else None,b"eng"):
            self.close()
            raise RuntimeError("Native Tesseract initialization failed")

    def close(self):
        if self.handle:
            self.lib.TessBaseAPIDelete(self.handle)
            self.handle=None

    def tsv(self,image,psm,whitelist):
        image=image.convert("L")
        data=C.create_string_buffer(image.tobytes())
        h=self.handle;lib=self.lib
        lib.TessBaseAPIClearAdaptiveClassifier(h)
        lib.TessBaseAPISetPageSegMode(h,psm)
        if not lib.TessBaseAPISetVariable(h,b"tessedit_char_whitelist",whitelist.encode("ascii")):
            raise RuntimeError("Could not configure OCR whitelist")
        lib.TessBaseAPISetImage(h,data,image.width,image.height,1,image.width)
        lib.TessBaseAPISetSourceResolution(h,70)
        ptr=None
        try:
            ptr=lib.TessBaseAPIGetTsvText(h,0)
            if not ptr:
                raise RuntimeError("Native OCR returned no TSV")
            # The C API returns rows without the CLI's header.
            raw=C.string_at(ptr).decode("utf-8",errors="replace")
            return "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"+raw
        finally:
            if ptr:lib.TessDeleteText(ptr)
            lib.TessBaseAPIClear(h)

def prepare_native(exe):
    if not exe or exe in _failed or os.environ.get("POKER_OCR_CLI")=="1":
        return None
    if exe not in _instances:
        try:
            _instances[exe]=NativeOCR(exe)
        except (OSError,RuntimeError,AttributeError):
            _failed.add(exe)
    return _instances.get(exe)

def backend_name(exe):
    return "native persistent" if prepare_native(exe) else "CLI fallback" if exe else "unavailable"

def recognize_tsv(image,exe,psm=11,whitelist="",*,persistent=False):
    engine=prepare_native(exe) if persistent else None
    if engine:
        try:
            return engine.tsv(image,psm,whitelist)
        except (RuntimeError,ValueError,OSError):
            engine.close()
            _instances.pop(exe,None)
            _failed.add(exe)
    # Avoid temporary file I/O in both CLI and persistent paths.
    data=io.BytesIO();image.save(data,format="PNG")
    command=[exe,"stdin","stdout","--psm",str(psm)]
    if whitelist:command+=["-c","tessedit_char_whitelist="+whitelist]
    proc=subprocess.run(command+["tsv"],input=data.getvalue(),capture_output=True,timeout=20,check=True)
    return proc.stdout.decode("utf-8",errors="replace")

@atexit.register
def close_all():
    for engine in _instances.values():engine.close()
