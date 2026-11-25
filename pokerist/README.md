# Pokerist screenshot review (experimental)

This optional local tool reads a saved screenshot after a hand. It is separate from the live table tracker and does not connect to Pokerist or feed advice into a game. Use only for review or other permitted analysis.

From the repository directory on Windows:

    py pokerist/review.py

Each launch automatically runs pip install against the complete requirements.txt using the same Python interpreter. Already satisfied requirements are reused; missing dependencies are installed. If installation fails, the program stops before importing Pillow or NumPy. Tesseract is an optional external executable and is not installed by pip.

Choose a saved landscape screenshot. The script prints unverified candidates and saves pokerist-review.json. You can also specify the screenshot as an argument.

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg"

Optional number OCR requires a separately installed Tesseract executable. If not on PATH:

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg" --tesseract "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

The 1536x709 five-seat layout and rank glyphs J, 4, 9, Q and 3 were calibrated from the supplied screenshot. Other ranks, alternate layouts, bet fields, dealer and active-player tracking are not yet calibrated. A template match is a candidate, not a validated reading; all values should be reviewed. No screenshots are stored in the repository or sent anywhere. No real-time screen capture, automatic actions or live recommendations.

## Profile indicators and seat changes

The optional review output now includes experimental seat evidence. A bright green segment plus red or amber in a profile-base crop produces a multicolor-band candidate. One unique candidate is reported separately from the unverified active-player field. Multiple candidates are marked as conflicting. A saved previous screenshot can be used to measure brightness and appearance changes:

    py pokerist/review.py later.jpg --previous earlier.jpg

Darkened avatars can correspond to nonactive, folded, or obscured players. A large appearance change may be a departure or animation; neither is promoted to a fold or departure automatically. Yellow/orange regions near approximate bet locations are searched for the literal ALL IN label using optional Tesseract. Color alone never implies all-in. Absence of OCR text remains unknown. These cues require positive screenshots for calibration; they do not drive the table tracker or live recommendations.

Run synthetic cue tests:

    py -m unittest discover -s pokerist -p "test_*.py"

## Full saved-video throughput diagnostic

Install FFmpeg and FFprobe on PATH. Record a completed local practice session at 60 FPS, then run:

    py pokerist/benchmark_video.py "C:\\path\\to\\recording.mp4"

The report includes decoded/processed counts, source timestamp gaps, measured wall-clock FPS, median/p95/worst per-frame latency, and OCR errors. The default includes OCR; `--no-ocr` is a visual-only diagnostic and cannot pass the full command's exit gate. A throughput pass does not establish field accuracy. Use the labelled saved-frame and field-coverage audits separately. The benchmark does not connect to a live game or feed advice. No 60 FPS result is claimed without measurement.

## Ground-truth completeness

    py pokerist/audit_manifest.py

This writes `manifest-coverage.json` with the exact missing labels for every saved screenshot. Explicit zero and empty card slots count as labelled; omitted observations do not. The current 18-image calibration corpus has 149 of 360 required labels. This is not a measured accuracy rate. A nonzero exit status means label coverage is incomplete. Fill missing fields only from inspected original images, not OCR predictions.

Saved video throughput diagnostics now reject changing frame dimensions before raw decoding. The report also records a hash of the ordered decoded pixel frames and counts adjacent identical pixel frames separately from duplicate presentation timestamps. Identical pixels may represent a legitimately static table. Coverage and throughput still do not establish that every visual event was recorded or correctly recognized.

## Frame coverage and incremental benchmark

The authorized practice capture now queues each browser-presented frame in order. Missing callbacks and overload are counted explicitly while recognition continues; queued frames remain in sequence. After saturation, new frame admission resumes when the queue drains below its low watermark. Mismatched responses and duplicate or out-of-order callbacks remain fatal. Display refresh is separate. The source and processing rates are independently reported. Browser-presented frames are not a guarantee that the source delivered every physical frame.

    py pokerist/benchmark_video.py recording.mp4 --incremental --target 60

This measures completed-recording decoding and recognition using exact OCR-mask and card-region caches. Every changed region is reconsidered; unchanged input can reuse a candidate. This does not establish recognition accuracy or guarantee live 60 FPS. OCR subprocess latency and PNG transport remain possible bottlenecks.

Recognition startup now prepares the local Python worker before starting frame accounting. Stop/restart cancels abandoned requests. A replacement session has its own sequence counter. The initial preparation time is not included in capture throughput; the displayed counters start when the worker is ready. This does not guarantee 60 FPS source capture or OCR throughput.

Coverage losses are not recovered frames. Temporal observations reset at the next accepted frame after a gap; stale results are not shown as fresh. A degraded run cannot establish complete 60 FPS coverage.

The incremental worker tries the installed Tesseract shared library first (persistent initialized handle), with CLI stdin fallback. The frame telemetry identifies the OCR backend. Set `POKER_OCR_CLI=1` before starting the server to force the compatibility path. Native OCR uses the same language and whitelist but output can differ from CLI; saved review keeps CLI recognition. Empty prepared masks bypass OCR without inventing chip values.

The saved-recording benchmark now reports decode/hash, normalization and recognition latency separately (median and p95), and identifies the actual OCR backend. Dealer matching reuses exact unchanged search-window results; changed windows are matched again. OCR misses reuse the prepared bitmap rather than running preprocessing twice.

### Controlled synthetic throughput diagnostic

Run `py pokerist/benchmark_synthetic.py --frames 180 --change-every 12` to measure offline processing with known numeric text that changes regularly and background pixels that change every frame. Use `--change-every 1` for a stress case. The report separates median/p95/max latency, OCR errors and synthetic numeric accuracy. This test is not a real Pokerist image accuracy test or a live capture benchmark.
