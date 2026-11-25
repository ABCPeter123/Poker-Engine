"""Persistent local recognition worker for permitted private practice or saved review."""
import base64
import io
import json
import os
import shutil
import sys
import time

from bootstrap import ensure_requirements
ensure_requirements()
from PIL import Image
from review import normalize, review_image
from ocr_runtime import resolve_tesseract

PREFIX = "POKER_FRAME "
tesseract, ocr_error = resolve_tesseract()
previous = None
previous_session = None
last_ocr = 0.0
Image.MAX_IMAGE_PIXELS = 12000000

def send(data):
    print(PREFIX + json.dumps(data, allow_nan=False), flush=True)

send({"ready": True, "ocr": bool(tesseract), "ocr_error": ocr_error})
for line in sys.stdin:
    request_id = None
    try:
        req = json.loads(line)
        request_id = req["id"]
        session = req["session"]
        raw = base64.b64decode(req["png"], validate=True)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Frame too large")
        with Image.open(io.BytesIO(raw), formats=["PNG"]) as original:
            if original.width * original.height > 12000000:
                raise ValueError("Frame dimensions exceed limit")
            image = normalize(original)
        if session != previous_session:
            previous = None
            previous_session = session
            last_ocr = 0.0
        # OCR is optional and expensive. Keep the fast card/visual path independent.
        now = time.monotonic()
        use_ocr = tesseract if req.get("ocr") and now-last_ocr >= 3 else None
        comparable = previous if previous is not None and previous.info.get("capture_crop")==image.info.get("capture_crop") else None
        result = review_image(image, use_ocr, comparable, "private practice frame")
        previous = image
        if use_ocr:
            last_ocr = now
        requested = bool(req.get("ocr"))
        scan_error = result.get("table_observation", {}).get("ocr_warning") if use_ocr else None
        number_error = result.get("number_ocr_error") if use_ocr else None
        cue_error = result.get("seat_evidence", {}).get("ocr_warning") if use_ocr else None
        state = "disabled" if not requested else "unavailable" if not tesseract else "failed" if use_ocr and (scan_error or number_error or cue_error) else "sampled" if use_ocr else "waiting"
        send({"id":request_id, "result":result, "ocr_sampled":bool(use_ocr),
              "ocr_status":{"state":state,"detail":ocr_error if state=="unavailable" else scan_error or number_error or cue_error if state=="failed" else None}})
    except Exception as exc:
        previous = None
        send({"id":request_id,"error":str(exc)})
