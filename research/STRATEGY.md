# Poker strategy research and offline validation

The current random-hand showdown equity model is not a multiplayer no-limit solver. The simplified raise model assumes opponents match the extra wager and unchanged equity. These assumptions cannot establish a strong strategy or account for future betting.

## Literature

- Brown and Sandholm, *Superhuman AI for multiplayer poker*, Science (2019), DOI https://doi.org/10.1126/science.aay2400. Pluribus used self-play to compute an abstract strategy, then depth-limited search to refine it. It is not a collection of hand-strength thresholds.
- University of Alberta Computer Poker Research Group, https://poker.cs.ualberta.ca/publications.html. Opponent modelling and exploitation require observations of strategies, not isolated guesses about hidden cards.
- *Synergistic Information Processing Encrypts Strategic Reasoning in Poker*, https://doi.org/10.1111/cogs.12632. Betting actions can reflect both private strength and public opponent signals. Avatar appearance is not a reliable measure of a person's playing style.

## Implementation in this commit

The offline range-study module compares the same verified completed-hand scenario under uniform and synthetically stronger opponent ranges, reports showdown-only EV and simulation standard error, and provides a smoothed frequency estimator with explicit opportunity counts. It does not change the live overlay's strategy. The existing tight/loose sampling styles are heuristic, not calibrated ranges.

## Required future research

1. Collect verified hand histories with position, effective stack, betting sequence, legal actions, sizes, and showdown information where available.
2. Establish a reproducible local simulation benchmark with held-out seeds, varied opponents, paired comparisons, chip profit per 100 hands, confidence intervals, and exact legal-state validation.
3. Train and evaluate abstract self-play policies (e.g. CFR variants) in the local simulator before attempting any stronger strategy claims.
4. Study opponent tendencies using opportunity-normalized frequency estimates and uncertainty; avoid inferring psychological traits from a single bet or an avatar.
5. Evaluate range and continuation assumptions, and quantify sensitivity to incomplete observations.

No claim of professional-level play or measured improvement is made.
