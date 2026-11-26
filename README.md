# Poker Engine

A dependency-free, local Texas Hold'em play-chip analysis and practice panel, following the Quant-Comp-2026 Liar's Market architecture: pure engine, browser app, card picker, Monte Carlo, local storage and Node tests.

## Start (Windows, macOS, Linux)

Install Node.js 18 or newer. From the repo root:

    npm start

Open http://127.0.0.1:8000. No npm install, API keys, accounts, Vercel or external dependencies needed. Alternatively serve the folder with `python -m http.server 8000 --bind 127.0.0.1`.

    npm test

## Table tracker (default homepage)

The table is always visible. Before a hand starts, tap ME and D on fixed seats to select your seat and dealer, edit stacks in place, and adjust blinds above the table. Zero-stack seats sit out. Click Start hand to post blinds. Enter your two cards with the picker. Record each highlighted player's actual check, call, fold, raise-to or all-in. The engine posts blinds, rotates action clockwise, closes streets, refunds uncalled chips and calculates side pots. Reveal community cards at each street break; choose observed winners at the end, including ties. Next hand rotates the dealer past empty seats and carries stacks forward without moving or renumbering seats. The next hand opens in editable pre-hand mode so you can rebuy or adjust stacks before posting blinds. During betting, correct a remaining positive stack in place; use undo for incorrect bets, folds or all-in status. Undo restores the previous table state. The recommendation panel only evaluates when it is your turn; it uses the existing showdown equity model and simplified chip EV, suppressing raises where side pots or unequal effective stacks make the model unsuitable. No opponent action is automated. Standard no-limit play-chip model: no antes, straddles, rake or tournament ICM. The previous standalone analysis/practice tool is at /analysis.html.

## Fast entry

- Tap Check / Call, Fold or All-in once. Raise presets execute the displayed raise-to amount in one click. Enter a custom total and press Enter.
- Keyboard (when no field is focused): C check/call, F fold, A all-in, R focus raise amount, U undo, H focus hole card entry, B focus board card entry, N start hand / continue street. Escape exits a focused field.
- Enter cards as AsKd, or 7h 10c 2d. A complete hand/board replaces its respective cards; shorter sequences append. Auto-advance (default on) starts the next street as soon as the required community cards are entered. Toggle it off for manual confirmation.
- Batch actions: c f r30 c means check/call, fold, raise to 30, check/call in the observed order. Explicit check/k/x, call, fold/f, a/all-in, rNUMBER/bNUMBER supported. A batch is atomic and cannot cross a street boundary. Undo reverses the entire batch.
- Select a single winner directly when all contested pots have the same eligible seats. For splits or differing side-pot winners, use checkboxes. Settle + next hand rotates the dealer and opens the editable table, without a separate confirmation screen.

## Equity lab workflow

- Hand analysis: select two hole cards, then tap community cards as the flop, turn and river appear. Update the active opponents, eligible pot, call amount and remaining stack.
- Practice deal: a local random deal shows your cards; reveal streets one at a time, then reveal opponents at showdown. This is a card/equity drill, not a full interactive betting game.
- Compare equity, win/tie/loss, pot odds, and simplified chip-EV scenarios. Record observed results and export history. Browser storage preserves the workspace.
- The background worker cancels old simulations on edits. Random seed makes results reproducible.

## Mathematical assumptions

Equity is fractional expected showdown pot share (ties split equally). The exact heads-up river calculation enumerates all 990 opponent combinations under a uniform range. Other cases use Monte Carlo without replacement. Tight and loose options are illustrative biased starting-hand samplers (best of five or two random candidate pairs), not empirical or GTO ranges. Multiway draws are sequential, not independent conditional range distributions. The reported standard error reflects sampling noise, not range or model error.

Call EV = equity × (eligible pot + call) − call. Check is a free-showdown proxy. Raise EV is shown only heads-up when a valid user-entered raise size is supplied; it assumes the opponent folds at the entered rate or matches the excess raise with unchanged equity. It excludes future betting, side-pot allocation, rake, and opponent stack caps; enter the eligible pot and a feasible raise. Position is recorded but not used to infer ranges. This is not a GTO solver or a complete betting rules engine. Practice deals do not model wagering, deposits, real-money play, or external game integration.

## Project layout

- engine.js: pure evaluator, seeded equity, chip EV, practice deal and showdown
- worker.js: browser Monte Carlo worker
- app.js, index.html, styles.css: interface and local persistence
- server.mjs: loopback-only static server
- tests/: Node regression tests

## Screen review and practice HUD

Open /screen-review.html in Chrome or Edge on localhost. Choose an already mirrored window with Share a window; the browser asks for permission each time. Or open a saved recording or image. Freeze a frame and draw on it using mouse or touch; Clear drawing resets the annotations. Stop sharing releases the capture tracks. Live shared-window frames are never sent to a server or used as strategy inputs. For saved recordings or screenshots, freeze a frame and click Analyze saved frame. The loopback Node server invokes the existing Python recognizer on a temporary PNG, returns unverified card and number candidates, and deletes the temporary files. Python requirements are checked automatically; optional Tesseract must already be installed. First analysis may take longer. The endpoint accepts only same-origin localhost PNG requests, at most 8 MB, and one review at a time. No recommendations are generated from imported media. iPhone mirroring requires a separate compatible receiver on Windows.

Open /analysis.html?practice=1 to see the local generated-deal HUD. It overlays equity, pot odds, and highest modeled chip-EV action on the simulated table as you reveal streets. It is not connected to screen capture or Pokerist. The offline screenshot parser also remains available as a standalone command.

### Saved recording navigation

Use the timeline and ±1-second controls to seek a saved recording and freeze the selected frame. Analyze saved frame shows candidates and flags duplicate cards or noncontiguous community-card slots. Export review JSON includes the recording timestamp. The rank/suit recognizer accepts multiple glyph templates for a single symbol without treating those variants as competing labels. Calibration still covers only the supplied five ranks and layout; no live recognition or recommendations are connected to the shared-window preview.

Saved-frame verification: after recognition, correct the card and chip fields against the frozen image, then confirm and export a verified JSON record. Unknown fields stay null; rounded amounts stay approximate. OCR results with confidence below 75 are withheld from prefilled values. No imported media feeds strategy decisions.

### Live preview quality and sizing

Screen Review defaults to a 720-pixel-wide preview, constrained to 55% of the viewport height. Small, medium, large and native/fit options change only display size, never the underlying frame. Fullscreen is available. The browser requests high-resolution capture and 30 FPS detail mode (or 60 FPS smooth mode); actual capture settings depend on the browser and UxPlay source. Incoming pixel dimensions, measured FPS, and cumulative dropped-frame fraction are shown during mirroring. Preferences persist locally. If incoming resolution is low, enlarge the UxPlay window and reconnect. No live screen frames are submitted for poker recognition or recommendations.

### Landscape mirroring

Disable portrait orientation lock on the iPhone, open the app in landscape and use UxPlay with `-s 1920x1080 -fps 30`. Auto orientation follows the incoming video dimensions and resizes on source changes. If the captured window contains sideways video, choose Rotate left/right or 180 degrees. The rotation preference persists and applies to frozen frames and drawings too. It does not change the iPhone or UxPlay's native orientation, and does not remove black borders inside a captured window.

### Native AirPlay window fitting (Windows)

Stop the old UxPlay process, then run `py start_mirror.py` from the repo root. The launcher starts your existing UxPlay installation using a Direct3D11 sink that preserves source aspect ratio, with 1080p requested and a dedicated fixed password by default. Enter the same password (at least eight ASCII letters/digits) each launch. Select the new Private Mirror Secure receiver on iOS. Its stable, separate advertised identity avoids reusing the earlier PIN pairing. The password is not saved by the launcher or printed, but is passed to UxPlay in its process arguments; local processes may be able to read it. Do not reuse an account password. UxPlay's digest authentication is limited protection for a trusted private LAN. `--auth random` uses the previous rotating password flow; `--auth pin` uses Apple's PIN pairing as an optional alternative. It reads UxPlay's reported stream geometry and resizes only that process's visible native window on each geometry change. Older UxPlay builds may not report the supported geometry format; the sink still preserves the aspect ratio, but window auto-sizing then requires a newer build. Use `--software` if the GPU decoder fails during rotation or `--exe` for a different install location. Ctrl+C stops the receiver. It does not install software or modify the phone, firewall, or UxPlay source. Browser sharing is still a separate explicit permission.

Confirmed saved-frame review can now calculate showdown equity through the same worker as the practice engine, after you select the observed number of opponents. No live capture frames are sent to recognition or strategy analysis. No best-action recommendation is generated from a third-party game's media.

The native mirror launcher also listens for negotiated Direct3D11 sink caps so it can react when the decoder changes resolution without a new AirPlay geometry message. It retries resizing while a renderer window is being created. If your GStreamer build does not expose these debug messages, launch `py start_mirror.py --landscape` to force the native window to the wide 1536:709 aspect observed in the example, without stretching the video. Normal mode remains automatic. This fallback is for landscape-only sessions.

## Authorized private-practice live recognition (experimental)

After sharing a window, enable the permission checkbox only for a private practice environment that explicitly permits real-time analysis, then Start recognition. The local persistent Python worker checks requirements once at startup and samples frames sequentially, without a backlog. It stops after 30 seconds of inactivity. Two successive complete identical card candidates are required before calculating benchmark equity against a manually supplied opponent count. Missing/duplicate/conflicting cards clear the equity. Optional OCR samples stack and pot candidates, not exact bet accounting. Stop recognition releases the client loop; Stop sharing releases the capture. No automated actions or best-action recommendation. Never enable this on a platform that forbids real-time assistance; use saved recording review instead. Recognition remains calibrated to only the original five ranks and five-seat landscape layout. Frames are processed locally, without storing screenshots or uploading to external services.

### AirPlay missing from browser window picker

Connect the phone and restore the native video window before sharing. The launcher attempts to label its own renderer `AirPlay Mirror (UxPlay)` for easier selection; some renderers may retain their original name. Screen Review prefers the window picker; use Compatibility picker to omit advanced constraints or Entire screen for a preview-only fallback. The browser always requires manual source selection. Switching sources preserves the prior capture if the picker is cancelled or a new source cannot start. The viewer reports stalled/muted capture, and requires a new explicit selection if the track ends. Entire-screen capture may include private information and cannot start the practice recognition panel. No browser flags or security settings need to be disabled.

### Captured window normalization

The recognition backend strips near-black outer padding and a detected light Windows title bar before comparing against the calibrated landscape geometry. It does not arbitrarily stretch an unsupported window into the expected layout. The result includes original frame dimensions, crop bounds and visible dimensions. A 1102 × 540 receiver frame with a 29-pixel title bar becomes approximately 1102 × 511. Unsupported layouts still produce an explicit error. Cropping fixes geometry only; missing hero cards and unsupported ranks remain unknown. No change to the existing authorized-practice restriction.

### Preflop logo regression

Card-face detection now requires sustained bright neutral card stock rather than the previous permissive brightness threshold. This rejects the pale Pokerist lettering when the board is empty. Rank/suit matching uses consistent red or black ink and limits suit candidates accordingly. Two observed hole-card coordinate variants and additional glyph templates cover the supplied J-heart/3-spade screenshot while retaining the earlier 9-spade/3-diamond layout. These are calibration samples, not a general accuracy benchmark. Other ranks and layouts can remain unrecognized. Use only for offline review or authorized practice.

### Character and table diagnostics

The character matcher now includes screenshot-derived 8, 7, 6, 10 and additional 4/9 and suit masks; 10 is represented as T internally. The wide hole-card crop captures both digits. The 2, 5, K and A ranks still need genuine glyph samples. The authorized-practice panel now displays each seat's candidate stack, visible bet, status text, card-back evidence, active band and dealer marker, with raw OCR and age of the last scan. Missing readings remain unknown. Dealer matching is calibrated against the supplied upper-right and right marker examples; other locations are estimated regions. Bet and status regions are experimental. OCR needs Tesseract installed. This is not a reconstructed betting ledger.

### Moving chip labels

Stack, pot and displayed-bet OCR now searches broad seat-relative regions rather than assuming digits start at fixed x coordinates. Sparse OCR returns word positions, grouped by text baseline, and the recognizer accepts only one plausible high-confidence amount line. It handles space-separated thousands and abbreviated amounts. Raw OCR and detected text bounds are retained; competing lines or malformed fragments remain unknown. This does not guarantee that a chip icon will never be read as a digit, or support seats outside the calibrated five-seat layout. Use saved-hand review or explicitly permitted practice only.

### Highlighted cards and participation evidence

All 13 rank labels now have corner-glyph samples. New red K, black A, red/black 2, black 5, black Q, highlighted red J and highlighted black J samples come from the supplied saved screenshots. The character mask separates red ink from warm gold outlines and black ink from colored artwork; alternate corner regions handle the observed few-pixel shifts. The five-seat review reports `No participation detected` when there is no visible card, current-turn cue or explicit action evidence. This is an observation, not proof of folding or an empty seat; it does not automatically change the opponent count. Recognition accuracy on unseen frames remains unverified.

### Temporary card memory

In the permitted-practice view, each slot must be read directly twice before it can be held. A single missing or unreadable slot can retain its last value for at most five seconds and three missed samples if another card in that group still matches. Cached cards have an asterisk. A complete board disappearance, contradictory card, duplicate reading, source change or capture error invalidates prior memory; both missing hole cards are cleared immediately. Cached values are display-only and cannot seed or update the equity calculation. No new cards are invented. Saved-image review remains independent.

### OCR startup diagnostics

`py pokerist/ocr_runtime.py` checks whether the native Tesseract executable is available and can start. The worker and saved screenshot CLI discover common Windows install locations in addition to PATH, or honor the explicitly configured TESSERACT_CMD. The optional Python requirements do not install the native executable. The practice panel distinguishes unavailable, failed and waiting OCR instead of silently displaying an unsampled table. If unavailable, install Tesseract separately, or set `$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'` in PowerShell before `npm start`. Restart the server after changing the environment. This diagnostic change does not improve card recognition accuracy or enable competitive real-time assistance.

### Numeric OCR preprocessing

Stack and bet search strips are narrower vertically to avoid mixing the name/status line with chip amounts, and the upper-right bet search extends further right. Amount OCR uses a separate numeric whitelist; status labels retain normal language OCR. A heuristic mask removes a separated emblem-sized leading run from stack text and the span of a saturated chip from bet text. These masks are experimental and may remove a digit or miss a neutral chip, so all values remain unverified candidates; confidence below 75 is rejected. Raw OCR and confidence remain visible even on rejection. Each scan has a 10-second timeout. Tested an experimental preprocessing pass on the supplied screenshot, not a full end-to-end Windows run. Use only for saved review or explicitly permitted practice.

### Card-face anchored corner extraction

The review recognizer explicitly excludes gold highlight pixels from both ink masks. It locates the bright card face within the local search area and tries corner windows translated to the observed face, retaining the calibrated fixed windows as alternatives. Full board faces and narrow overlapping hole-card strips are handled separately. Candidate scores are grouped by card identity, and visible but unreadable faces remain unknown rather than being treated as empty. The existing temporary display-only memory and permitted-practice restrictions remain unchanged. The new geometry tests are synthetic; successful recognition on the three latest screenshots has not yet been verified.

### Reader regressions: wide ten, rotated eight and amount lines

Added corner masks extracted from the latest saved-image examples (10-spade, 8-diamond, rotated 8-heart, 3-heart). The wider board rank window is eligible only for the ten candidate; the standard window remains active for other ranks. Added a rotated second-hole-card alternative and a tighter suit crop. Stack strips include additional vertical padding and isolate the dense text band. An unrestricted OCR retry may rescue a rejected numeric reading only if the complete digits agree and the retry passes the original confidence threshold. This does not guarantee correct digits; particularly, both OCR modes can make the same mistake. The new tests exercise glyph identity and preprocessing, not a full captured-game session. Use for saved review or explicitly authorized practice only.

### Gold-bordered pair and observation timestamps

Added saved-image corner masks for the highlighted red and black fives and their diamond/spade glyphs. The red-ink mask also rejects warm orange pixels. These samples are calibration data, not an independent accuracy test. In the authorized-practice diagnostics, amount age is measured from image capture rather than completion of OCR; the status includes processing duration. Old amount readings are marked stale rather than presented as newly captured. The displayed mirror can advance during recognition, so the panel describes an earlier captured image and is not a synchronized betting ledger. No strategy or action logic changed.

### Repeatable saved-image checks

Run `py pokerist/check_saved_frame.py "PATH_TO_SAVED_SCREENSHOT.png" pokerist/fixtures/20261124-223659.expected.json --crop 88 21 805 352` for the supplied 889 x 833 screenshot. The expected observations are transcribed from the visible saved image; the original screenshot is not stored in the repository. For other screenshots, supply their own expected JSON and optional game-area crop. The checker reports matching, missing and incorrect fields separately, including incorrect high-confidence amounts and false empty slots. It returns a nonzero exit code when any expected observation fails. This is an offline test harness, not a change to live recognition or advice.

## Recognition quality audit

Do not treat template coverage as recognition accuracy. The saved corpus has 18 labeled user-provided screenshots and 64 visible card instances (62 empty slots). Originals are deliberately kept outside this public repository. The benchmark loads your local copies, applies original, reduced-resolution and JPEG variants, records missing and incorrect readings separately, and measures per-frame median/p95 latency. It defaults to a strict 100% visible-card accuracy gate, zero wrong identities, and no false empty-slot positives. Missing files fail the run rather than silently reducing the denominator. The optional OCR mode additionally checks explicitly labeled amounts and seat cues; all visual readings remain candidates. Example:

```powershell
py -m pip install -r pokerist/requirements.txt
py pokerist/benchmark_saved_frames.py "E:\Poker-Screenshots"
py pokerist/benchmark_saved_frames.py "E:\Poker-Screenshots" --ocr --variants original
```

The JSON report includes every frame/field; the manifest contains crop coordinates and expected observations. Original screenshots are not committed. The corpus is calibration/regression data, not a held-out test. A local isolated reproduction of the current card classifier (manual game-area crops, before template caching) measured 55/64 correct visible cards, nine missing, zero wrong, and 62/62 correct empty slots; downscaling to 75% yielded 36/64 correct. These are not live or full Windows pipeline measurements. Two experimental ink-mask replacements degraded original-image accuracy, so they were not adopted. Card reading is split from other recognition for repeatable measurement, and decoded masks are cached read-only. All-in OCR now sizes its montage from its actual region widths and rejects substring-only status matches. The automated workflow runs the JS/Python suites on Linux and Windows; the private image corpus is a separate local gate.

### Field-level regression protection

The saved-image benchmark now stores SHA-256 source image fingerprints, counts exact card frames, and accepts `--baseline earlier-report.json` to reject new wrong readings or any previously correct field becoming incorrect/missing on the same image and variant. `--max-p95-ms` optionally sets a processing-time limit. Missing or malformed slot arrays no longer score as correctly empty. This prevents inflated accuracy when a reader crashes or returns incomplete output. Synthetic integration tests exercise saved-file normalization, recognition output, and serialization with no external game interaction. The original-image corpus is still local and not a held-out test set.

### Offline multi-view card recovery (experimental)

Saved-image review can optionally run four contrast/sharpening variants when the original reader finds a visible but unreadable card. It preserves every previously recognized identity and empty slot, requires at least three agreeing recognized variants with no opposing recognized vote, rejects duplicate cards, and labels recovered candidates with their provenance. These are correlated views of the same pixels, not independent measurements. The saved-image upload endpoint uses the enhanced mode; the live worker remains unchanged. The CLI and benchmark expose `--enhanced`. All enhanced readings still require manual verification.

A local reproduction of the card classifier tested on the 18 calibration screenshots and two degraded variants per screenshot yielded the following counts (64 visible cards and 62 empty slots per variant): original 55 to 56, downscale 36 to 54, JPEG 31 to 32. No incorrect visible-card identities or false empty-slot positives occurred in the selected conservative configuration. Complete frames changed from 13 to 13, 4 to 11, and 0 to 0 respectively. These are calibration results, not held-out accuracy measurements or a full native Windows run. A two-vote version produced a wrong suit and was rejected. Enhancement increases processing time on incomplete images and does not address chip OCR or all other visual errors.

Compare both modes locally with the same image folder:

```powershell
py pokerist/benchmark_saved_frames.py "E:\Poker-Screenshots" --output baseline.json
py pokerist/benchmark_saved_frames.py "E:\Poker-Screenshots" --enhanced --baseline baseline.json --output enhanced.json
```

A strict accuracy gate can still fail even when the comparison shows improvements. Preserve the output reports locally.

### Additional saved-image OCR evidence

Enhanced saved-image review now displays three single-line OCR passes for each stack and the pot, alongside original OCR evidence. It may recover an otherwise rejected numeric candidate only when the original raw amount is syntactically valid, two independent preprocessing passes have confidence at least 75, and all valid readings agree. If readings disagree, the manual confirmation input is blanked instead of prefilling a disputed amount. Existing raw candidate data is retained for audit. No change to the live reader. The three passes are correlated readings of the same image, not proof of accuracy. Tested the preprocessing in a local experiment on 21 manually labelled amounts across four screenshots; several readings remained incorrect or missing, including high-confidence errors. No verified improvement in integrated accuracy is claimed. See `pokerist/fixtures/external_sources.md` for screened public screenshot sources. External images could be viewed but not downloaded into the development environment.


### Deep saved-image alignment experiment

An optional offline-only `--deep` mode runs the existing enhanced card reader, then tests eight offsets of three pixels in normalized-image coordinates for remaining visible unreadable slots. The alignment pass uses the same conservative three-agreeing-votes/no-dissent rule, preserves original and enhanced identities and empty slots, and records separate provenance for recovered candidates. It does not affect the live worker or the standard saved-image upload endpoint.

On an isolated reproduction of the classifier across 18 calibration images and their downscaled and JPEG variants, the additional alignment pass changed correct visible-card counts from 56 to 59 (original), 54 to 56 (downscale), and 32 to 32 (JPEG), with zero incorrect identities and 62/62 correct empty slots per variant. Exact card frames changed from 13 to 15, 11 to 12, and 0 to 0. A less conservative two-vote setting produced three wrong identities and was rejected. A separate distance-transform matching experiment was also rejected because it did not improve overall accuracy. These measurements are from previously used calibration images and isolated classifier code, not an independent full-pipeline test. The extra passes cost more time and do not improve chip OCR.

```powershell
py pokerist/benchmark_saved_frames.py "E:\Poker-Screenshots" --deep --baseline enhanced.json --output deep.json
py pokerist/review.py "E:\Poker-Screenshots\example.png" --deep --no-ocr
```

All readings still require human confirmation.

### Recognition performance and regression checks

The matcher now uses cached packed binary templates and exact integer XOR/popcount in place of per-template NumPy comparisons. The Hamming distance, grouping, threshold and ambiguity margin are unchanged. Repeated corner reads within a card reuse results only inside that image. A deterministic equivalence test compares the previous and current matchers across real template masks and seeded noise; CI also prints a standalone matcher microbenchmark. `py pokerist/benchmark_matcher.py` measures matching only, not the full pipeline. The saved review JSON now reports stage timings in milliseconds (seat cues, cards, amounts, table observation, total); `benchmark_saved_frames.py --ocr` reports the median per stage. No capture-rate guarantee follows from matcher speed. OCR is still synchronous in the existing practice worker, and slow deep review remains offline only. Fixed the missing `deep` keyword in `review_image`; integration tests exercise all three review modes.

### Round bet memory (authorized practice diagnostics)

The extracted table now shows both raw visible bet candidates and tracked round bets. Each seat starts at `0 (initial)`, not a verified zero. Two matching OCR samples are needed for ordinary increases; large increases require three unless repeated exact stack-plus-bet conservation supports them. Missing data retains the previous amount. Four consistent exact lower readings (three with stack conservation) can correct a wrongly high value or refund, rather than permanently sticking to a maximum. Approximate lower readings remain disputed. The Edit button can correct any seat immediately, including zero, and ignores earlier in-flight frames. Reset clears all seats. Two matching street observations are required to reset automatically; a new preflop hole identity or dealer also triggers a repeated boundary check. False transitions and repeated OCR mistakes remain possible, particularly when joining mid-hand. This is a diagnostic candidate ledger, not a reconstruction of actual wagers or a strategy input. Numeric extraction now rejects competing plausible lines, even when a competing line has low confidence, and reports number OCR errors directly. These changes do not establish improved raw card or OCR accuracy.

### Authoritative manual observation locks

The authorized-practice diagnostics include an always-available manual editor for each hole/board slot, street, pot, dealer, current player, and each seat's stack, round bet, status, visible cards and participation. Edits lock the field, including a zero amount or explicitly empty card (`-`). Automatic readings cannot overwrite locks; manual values are the authoritative displayed observations. Locks persist across OCR failure, detected street or hand changes, capture restarts and browser reloads using local storage. Auto releases one field; New hand / clear all locks explicitly clears everything. Reset automatic bets does not clear manual locks. Raw OCR remains separate. No screenshot data is stored by the lock layer. Automatic practice equity is paused when manual cards or street are locked, rather than calculating against potentially conflicting raw cards; no strategy or action execution was added. Manual locks do not prove actual game state and must be updated when the underlying value changes. The existing permission requirement for live recognition remains unchanged.

### Direct mirror editing (authorized private practice)

Five approximate seat overlays expose stack and round bet directly on the shared-window preview. All unlocked inputs show automatic observations by default. Typing and pressing Enter or leaving a changed input locks only that field; A/Auto releases it. Clicking a seat opens its status and participation controls, while Cards / table edits the global fields. Manual locks and browser persistence are unchanged. Overlay controls do not send clicks or actions to the mirrored game. The model panel is limited to check/call/fold in explicitly permitted private practice, based on effective cards, fresh amounts, confirmed opponent count and the stated no-side-pot/inclusive-pot assumption. It suppresses output on missing/stale/contradictory inputs and unsupported short all-ins; it is a simplified showdown-equity model, not a full betting strategy. No automatic betting is implemented. The mirror anchors are approximate and actual layout fit requires testing on the Windows device.

### Decision status visibility

The existing private-practice decision status is displayed independently of the card overlay, at the bottom right of the shared preview and in a persistent status panel below the recognition controls. The mirror status stays visible when OCR fails or recognition is stopped. Both displays show the same reason when a decision is unavailable. No recommendation eligibility rules or calculations changed. The full-screen layout still needs visual verification on the target device.

### Compact amounts and saved-image grayscale OCR

Numeric grammar now handles case-insensitive K/M suffixes, detached suffix tokens, decimal abbreviated labels, and properly grouped integer amounts. Abbreviations retain an approximate flag and displayed precision; they are not confirmed exact balances. Ambiguous fragments, character substitutions and overflow are rejected. Enhanced offline saved-frame review adds two batched grayscale contrast passes preserving antialiasing instead of thresholding every pixel. The alternate crop is calibrated to the supplied five-seat stack/pot regions and may fail on other layouts or long text. Raw competing evidence is displayed for manual verification; no acceptance thresholds were reduced. An isolated local experiment on 21 manually labeled amount crops from four existing screenshots gave 21/21 raw correct readings for the stretch variant when batched per screenshot, with OCR process time approximately 0.12–0.18 seconds per batch; some confidence scores were zero. This is not the integrated accepted-candidate accuracy, not an independent test and not a Windows latency measurement. The enhanced OCR path is saved-image only. The shared grammar improvements also handle abbreviated numeric candidates in existing authorized-practice recognition. No incomplete-data action recommendation changes were made.


### Completed-recording coverage and bottom-bar evidence

A sparse screenshot sequence cannot reconstruct the exact order of actions that happened between frames. Audit a completed local recording with FFprobe (installed separately) to count actual timestamped frames, check duplicate/missing timestamps and report long gaps. Optionally provide manually labelled action visibility windows as a JSON array of objects with `label`, `start_s`, and `end_s` (seconds on the recording timestamp clock). A sample in a window does not establish that the action was readable.

```powershell
py pokerist/audit_recording.py "E:\Poker-Screenshots\completed-hand.mp4" --max-gap-ms 100
py pokerist/audit_recording.py "E:\Poker-Screenshots\completed-hand.mp4" --events labelled-windows.json
py pokerist/saved_bar_evidence.py "E:\Poker-Screenshots\saved-frame.png" --crop 180 310 700 342
```

The bottom-bar tool preserves the original crop and two raw OCR readings. Adjust the crop to the actual saved image. It does not infer whether buttons are enabled or whether an action is legal. In particular, preselection controls and combination-bet buttons are distinct from ordinary Hold'em decisions. The earlier grayscale amount grammar tests passed on Windows and Linux, but no parser guarantees correct extraction from ambiguous pixels. The local manual table simulator already supports conditional heads-up raise evaluation from explicit legal bounds and assumed fold probability. Neither diagnostic script connects to a live capture or changes the external-game recommendation path.

### Numeric benchmark acceptance audit

Saved-corpus reports now distinguish raw text accuracy for each OCR method from the accepted candidate accuracy. Disputed fields blanked by the review interface count as missing, even when the retained raw candidate happens to be correct. Abbreviated amounts are compared against their labelled displayed magnitude, not an inferred exact balance. OCR failures prevent the quality gate passing. Numeric labels must be valid nonnegative whole chip amounts, and comparisons pair identical input bytes, crops and expected labels. Older reports without crop metadata may need regenerating. The current calibration manifest has 21 labelled numeric fields over four images. No live capture, action interpretation, or recommendation changes.

### Character recognition study (saved-image only)

The new glyph audit separates segmentation failures from character matching failures, comparing binary and grayscale normalized glyphs with aspect ratio retained. Its input consists of manually localized, labelled saved-image crops. Entire image groups are held out of training. Ground truth selects a segmentation with the correct character count, so the results are optimistic diagnostics, not a usable automatic reader. The four-image calibration experiment found 18/21 segmented lines, 65/69 correct characters in those lines, and 15/21 correct full labels for both feature modes. The held-out K and decimal classes have no training exemplars in other images. This prototype is not connected to capture or the engine. The same audit can evaluate independently labelled rank/suit patches by specifying dark_ink for dark characters on light card stock; no card-specific accuracy improvement is claimed. Run:

```powershell
py pokerist/glyph_audit.py "E:\Poker-Screenshots" pokerist/fixtures/glyph_amount_crops.json
```


### Automatic segmentation and held-out card crop evaluation

`automatic_glyph_audit.py` is a completed-image research tool, not a runtime reader. Training uses labelled crops; amount inference tries multiple projection thresholds without receiving the target text or its length. Conflicting segmentations are rejected. The card comparison keeps entire repeated-hand groups together, tests rank and suit separately, and compares binary vs grayscale features without a test-hand template. The crop coordinates remain manually localized and the ten crop was manually widened, so this is not automatic full-frame accuracy. The decision thresholds were explored on this calibration corpus and need independent validation. The saved and live production readers remain unchanged.

```powershell
py pokerist/automatic_glyph_audit.py "E:\Poker-Screenshots" pokerist/fixtures/glyph_amount_crops.json --kind amount --output amount-audit.json
py pokerist/automatic_glyph_audit.py "E:\Poker-Screenshots" pokerist/fixtures/glyph_card_crops.json --kind card --output card-audit.json
```

### Completed-hand review corrections

Enhanced saved-image review now presents parseable numeric alternatives as individually selectable evidence, including low-confidence grayscale OCR. Conflicting amounts no longer leak as accepted stack/pot candidates: the original is retained separately for audit. Multi-view card evidence remains available when the reader cannot settle a visible card identity. The saved review editor preserves each card position and distinguishes an unreadable slot (`?`) from an empty slot (`-`). Individual known cards, visible bets, stacks, pot, dealer and turn cue can be confirmed and exported even when the rest of the hand is incomplete. Equity still requires a complete valid confirmed deck. The manual amount parser accepts K/M, exact whole chips and valid grouping. This does not promote alternate OCR to truth or change live capture. The offline classifier experiments on the four calibration images returned 16/21 matching complete numeric labels with unknown-length projection segmentation (local reconstruction, not full-screen testing); the 46 board crop study returned 29 correct and no wrong accepted binary card labels vs 33 correct and three wrong grayscale labels. Neither classifier is sufficiently validated to replace the reader automatically.

### Saved-review visual field evidence

Enhanced/deep completed-image reviews now return lossless PNG crops from the normalized source image for each card, stack, pot and visible bet. The review editor displays these alongside the corresponding input. For visible unreadable cards, separately accepted rank and suit matches are retained with template distances and crop coordinates; they are never joined into an automatically verified card. This avoids discarding useful partial evidence while keeping uncertain components explicit. The baseline and live recognition modes do not generate these crops or component evidence. The output JSON for a saved review is larger because it contains local crop pixels; treat it like the original screenshot. No automatic accuracy improvement is claimed.

The local saved-frame bridge requests quiet CLI output so embedded crops cannot overflow the subprocess stdout buffer. On-page JSON hides the base64 strings for readability; exported raw review JSON retains them.

The saved review editor also accepts a confirmed partial rank (`A?`) or suit (`?s`), and component evidence buttons allow a human reviewer to enter either independently. These export as partial slots, not complete cards. Partial cards cannot enter equity calculations or occupy a slot after the selected street.

### Required-field completeness for saved-image reports

Audit an existing completed-image benchmark report with `py pokerist/audit_field_coverage.py saved-benchmark.json`. The report covers five stacks, five bets, dealer/turn cues, seven card slots and pot (20 fields). It separates manually unlabelled fields from recognition misses and incorrect readings, and requires every field in every expected frame to be labelled and matched for complete validation. Reported sequential-equivalent FPS is calculated from existing saved-image timings, excludes some I/O and decoding costs, and is not a sustained capture benchmark. No capture, recognition scheduling or recommendation changes are made.

### 60 FPS receiver request

Restart the AirPlay receiver as well as the browser/server. The Windows launcher now requests 60 FPS by default (`py start_mirror.py --fps 60`); use `--fps 30` for compatibility. Disconnect and reconnect iPhone mirroring and choose Smooth · 60 FPS in the browser. The negotiated frame rate may still be lower. Existing browser preferences are preserved.

### Windows mirror audio stability

Browser screen sharing is video-only; UxPlay renders audio directly to the Windows output device. The launcher now probes the installed GStreamer audio sinks in order (wasapi2sink, wasapisink, directsoundsink), uses the normal shared-mode defaults, and defaults to UxPlay's documented `-vsync no` live screen-mirroring mode. Timestamp-based playback remains available with `--audio-sync timestamp` if audiovisual synchronization is more important. Restart the receiver with `py start_mirror.py`; if audio still cuts out, try `py start_mirror.py --audio-sink directsoundsink` (or `--audio-sink wasapisink`). Audio-related GStreamer warnings are visible in the launcher terminal. The probe checks plugin availability, not physical device health; it does not recover a disconnected iPhone session or guarantee uninterrupted sound. Upstream reference: https://github.com/FDH2/UxPlay#readme . No browser audio capture or duplicated audio output is introduced.

DirectSound (`directsoundsink`) is now the receiver launcher default. If it is missing, the launcher reports the missing plugin; use `--audio-sink auto` for automatic selection. In the private practice workspace, equity simulations are cached per deck and opponent count. Changes to the observed count do not discard completed simulations of the same cards. Incomplete cards, failed simulations and missing numeric snapshots have distinct status messages. The cache is invalidated on card/hand resets; incomplete or contradictory evidence is not replaced by fabricated values. Full device validation remains necessary.

Hand observation continuity: the display retains previously consolidated cards, stacks, pot, dealer, turn and last action through missing samples, street changes, capture pauses, source geometry changes and OCR toggles. Current-street wager fields reset at confirmed street advances; cumulative observed contributions remain. The confirmed absence lifecycle marks the hand ended and freezes its displayed history until a new deal is recognized. Explicit source replacement or manual new-hand reset still clears history. Retained values are historical evidence and do not become fresh recognition merely because they remain displayed. This change does not validate the current cards or external game state.

Practice raise sizing now handles a conditional zero current-street commitment when the check prompt is explicit, the hero chip label is absent, the same street is confirmed and no prior nonzero or provisional hero wager conflicts. A rounded positive stack no longer prevents observation of an exact posted big blind. An optional practice big-blind field is available when blind OCR fails. If the conservative full-raise bound cannot be computed, the model displays its baseline rather than an unsized raise, with the specific sizing blocker. Bounds remain conditional and are not certified external-room minimums.

The observation headline can show a parsed call prompt independently of missing equity or a failed whole-frame OCR status. A same-street absent hero wager with no conflicting tracked commitment supports an explicitly approximate zero-commitment display. Otherwise the highest observed wager is displayed as a wager, not an exact call cost. The optional pot convention now defaults to collected pot plus visible current-street wagers, based on the supplied screenshot showing a 1.2K central pot and a separate 12K bet; select inclusive if the source already includes bets. Incomplete/rounded totals remain marked. This is a conditional practice accounting model, not a verified reconstruction of a live game. No automatic rule to call a blind based solely on suited cards was added.

Action observation uses whole individual OCR lines rather than concatenating unrelated text. Exact action words remain required; competing action labels are withheld. A cached alternate color mask can recover pale labels when the yellow-mask pass fails. Raw alternate text and conflicts are exposed in the observation table. An explicit hero Fold can be retained when the hero cards disappear; accepted same-street wager increases are displayed independently of the action text, without guessing a call or raise from chip movement. These are observation diagnostics, not a verified action sequence; an action that occurs entirely between sampled frames may still be missed. Tests cover synthetic OCR tokens, color masks and ledger updates, not new raw device captures.

The practice overlay now separates model action headlines (CHECK, FOLD, CALL with amount, RAISE TO with amount) from observed prices. NO SUGGESTION indicates incomplete or unresolved inputs, not a recommendation to fold or call. Conditional estimates retain their qualification; detailed model diagnostics are below the preview in the expandable Model diagnostics section. This is a presentation change only, not a new strategy or a guarantee of valid live inputs.

Right-seat action observation now includes a conservative fixed-font fallback calibrated from four action labels in saved right-seat screenshots. The two November 26 screenshot crops of Fold match the saved Fold templates (distance .134); these two screenshots show the same action, not independent hands. Accepted explicit folds persist in the participant observation until the next hand, with manual overrides. This fallback is only calibrated for the right seat; OCR remains primary. Offline strategy research and range sensitivity analysis are documented in `research/STRATEGY.md` and `research/strategy-study.mjs`. The offline study does not change the live recommendation strategy.
