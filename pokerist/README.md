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

The Offline recognition performance workflow runs both regular changes and every-frame changes with installed Tesseract on Linux. Its reports include correct/incorrect/unknown counts for all five stacks, five bets and the pot, plus exact raw-region cache hits. These controlled synthetic results are diagnostic only, not real capture throughput or real screenshot accuracy. The raw RGB crop shortcut reuses a reading only when the crop bytes and OCR configuration are identical; changed crops still undergo the existing mask checks.

Current-state practice mode now counts video callbacks but admits only a fresh snapshot when the previous request has completed, with a minimum 100 ms interval. It does not queue historical screenshots, and deliberate sampling is tracked separately from source gaps. Automatic screen/numeric data expires after one second in the view. A tracked bet is displayed as current only when a fresh direct candidate agrees; a held historical amount is not treated as current. The completed-recording benchmark remains the way to measure every-frame coverage. Neither mode guarantees accuracy without verified evidence.

The current-state view inventories 20 requested fields (seven card slots, dealer, turn, pot, five stacks and five bets), distinguishing unknown, approximate, candidate and manual values. A separate adjacent-snapshot conservation diagnostic compares the same identifiable hand/street, exact stack candidates and pot change. Derived hypotheses and conflicts are diagnostic only; they do not populate automatic bet inputs or establish accuracy. A missed or ambiguous baseline invalidates the check.

The incremental numeric OCR path packs tightly cropped ink regions into a compact aligned text block (PSM 6), preserving each region's source-coordinate offset and rejecting words crossing row boundaries. Saved-image CLI review retains its original sparse montage. The synthetic performance workflow measures the change; benchmark results do not establish real screenshot accuracy.

### Local font-template calibration

`py pokerist/amount_glyph_library.py "C:\\path\\to\\saved-screenshots"` builds normalized digit-shape templates from the existing `fixtures/glyph_amount_crops.json` labels. The originals are intentionally not committed. The output lists digit coverage and separately scores recognition on held-out image groups, including missing and incorrect readings. It exits nonzero if any digit class is absent or any held-out label is missed or incorrect. The generated library is an offline calibration artifact, not an automatically validated full-frame recognizer. Do not commit local screenshots or template artifacts without reviewing their contents.

### Offline independent-reader comparison

Run `py pokerist/hybrid_amount_audit.py "C:\\path\\to\\saved-screenshots"` to compare held-out font glyph recognition against native OCR. Optional `--vision-endpoint http://127.0.0.1:8081/v1/chat/completions --vision-model YOUR_LOADED_VISION_MODEL` adds a local multimodal server. No model is downloaded or launched. Only individual labelled crops are sent to the explicit loopback endpoint, never full screenshots or expected values. The vision model receives no proposed OCR text. All readers are evaluated separately; agreement is a candidate, and conflicting valid readings are withheld. The audit records latency and unknown/incorrect/correct counts, and is not wired into live recognition. Vision calls run for every crop in the offline audit to establish an unbiased baseline; selective calls could be evaluated separately later.

`py pokerist/benchmark_hybrid.py` compares glyph and native OCR readers on 32 synthetic text crops in four held-out rendering groups (font size, blur, noise, and scale). This is a regression diagnostic, not calibration for the actual game font. The hybrid audit also reports the counterfactual accuracy and call count of invoking the vision model only on non-agreement. Selective evaluation uses the same recorded offline predictions; it does not measure end-to-end latency. An agreement between two readers can still be wrong.

### November 25 real-font calibration

`fixtures/glyph_amount_nov25.json` contains 48 manually localized text labels across seven 1536×709 screenshots, grouped into two hands. It records the original JPEG hashes; the original images remain local. Use `py pokerist/amount_glyph_library.py YOUR_SCREENSHOT_DIRECTORY --manifest pokerist/fixtures/glyph_amount_nov25.json` to regenerate the library. A separate manual-crop held-out shape-matching experiment produced 44 correct whole-number readings, zero incorrect readings and four unknown abbreviated readings (the other hand lacked decimal/K examples). This is a small two-hand crop experiment, not a full-screen recognition guarantee. The showdown 4.7K label is a payout, not a wager. No absent amount was labelled zero.

### Independent real-font validation, second batch

`fixtures/glyph_amount_nov25_additional.json` describes 62 manually localized whole-number crops (19 distinct numeric labels) from ten additional screenshots. Group `hand3` has four observations and `hand4` has 58. Do not merge these samples into the original training library when reporting independent performance. A local test using the frozen 184-template library, eight segmentation thresholds and the preexisting distance/margin criteria yielded 54 correct, 8 unknown, 0 incorrect. A separate Tesseract CLI single-line comparison at confidence >=75 returned 10 correct, 52 unknown, 0 incorrect. Repeated labels are correlated; these are crop observations, not 62 independent hands or a full-screen validation. Source images remain local.

### Automatic saved-image crop audits

New `offline_font_review.py`, `offline_card_audit.py`, and `offline_ring_audit.py` scripts are completed-image diagnostics only. They are not part of the capture loop or decision engine. The font tool takes the locally generated glyph library and a manifest; it locates amount crops using fixed 1536×709 layout windows, rather than the manually supplied label crop. The card audit independently classifies board ranks and suits, withholding the entire hand group from training. The marker audit separates multicolor active bands from gold winner bands. `fixtures/glyph_amount_nov25_final.json` adds 35 visible numeric and 20 absent-label observations; `fixtures/board_ring_nov25.json` covers 22 screenshots in five groups. Original images stay local. Run the three tools with the original screenshot folder and the relevant manifest. The local prototype recorded 91 correct/6 unknown/0 incorrect visible amounts in the 97 observations outside the initial training set, and no false positive on the 20 explicitly absent labels. Card performance was 49 correct/18 unknown/6 incorrect for 73 visible board cards; 71 suits correct, all 37 empty slots correctly rejected. Marker development-set scores were 22/22 active observations and 21/22 winner observations. These are small, partly inspected development datasets, not independent full-game accuracy claims. No hero-card or live accuracy established.

### Rotated hero card diagnostic

The offline card audit now includes calibrated hero-corner positions, with geometry-only selection between upright, rotated and lower-contrast face candidates. The same hand is excluded from all training examples, including both board and hero cards. A two-enclosed-loop veto rejects unsupported rank 8 matches rather than promoting another candidate. Local development-set results: board 55 correct/18 unknown/0 incorrect of 73 visible cards; hero 34 correct/1 unknown/0 incorrect of 35 visible cards; 37 empty board slots and 7 empty hero slots correctly rejected. The relocated showdown hero cards in IMG_0429 are outside the calibrated region and excluded. Geometry and veto were developed using these screenshots; independent new-hand evaluation is still required. No live integration.

### Optional completed-image fallback experiments

Use `--fallback` on `offline_card_audit.py` or `offline_font_review.py` to compare the baseline with additional legacy-template and single-line OCR evidence. The card audit tries the earlier built-in rank/suit templates on unresolved glyphs, then PSM 13 OCR on unresolved board ranks (confidence >=80). The numeric audit tries grayscale and binarized PSM 7 OCR on unresolved localized labels and requires identical valid text with both confidence scores >=10. These two OCR variants share the same model and are not statistically independent; the confidence threshold was selected on the development set and must not be treated as a probability of correctness. Local development experiments recovered all six previously unknown numeric fields (97/97 visible and 20/20 absent), and the legacy fallback recovered 12 card observations; a separate single-line test recovered the seven remaining board ranks. These results are from the inspected development images; the exact repository fallback implementation and new images still require independent validation. No integration into live recognition or decision calculation.
