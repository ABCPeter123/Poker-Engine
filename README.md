# Poker Engine

A dependency-free, local Texas Hold'em play-chip analysis and practice panel, following the Quant-Comp-2026 Liar's Market architecture: pure engine, browser app, card picker, Monte Carlo, local storage and Node tests.

## Start (Windows, macOS, Linux)

Install Node.js 18 or newer. From the repo root:

    npm start

Open http://127.0.0.1:8000. No npm install, API keys, accounts, Vercel or external dependencies needed. Alternatively serve the folder with `python -m http.server 8000 --bind 127.0.0.1`.

    npm test

## Table tracker (default homepage)

Set seats, dealer, blinds and starting stacks. Enter your two cards with the picker. Record each highlighted player's actual check, call, fold, raise-to or all-in. The engine posts blinds, rotates action clockwise, closes streets, refunds uncalled chips and calculates side pots. Reveal community cards at each street break; choose observed winners at the end, including ties. Next hand rotates the dealer and carries stacks forward; busted seats are removed. Undo restores the previous table state. The recommendation panel only evaluates when it is your turn; it uses the existing showdown equity model and simplified chip EV, suppressing raises where side pots or unequal effective stacks make the model unsuitable. No opponent action is automated. Standard no-limit play-chip model: no antes, straddles, rake or tournament ICM. The previous standalone analysis/practice tool is at /analysis.html.

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
