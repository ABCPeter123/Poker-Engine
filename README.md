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
