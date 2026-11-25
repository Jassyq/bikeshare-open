# Report: bikeshare demand forecasting under an agent

## Results

"before" = without my feature, which is also the final pipeline: 14 features, `reports/metrics.json` from `make all` (identical to the starter's `reports/metrics_starter.json`). "after" = with `cnt_roll_3` as a model input: 15 features, `reports/metrics_with_cnt_roll_3.json`. I rejected the feature, so the committed `metrics.json` is the "before" rows.

| model | feature set | valid R² | valid MAE | test R² | test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6439 | 836.5 | 0.58 | 946.2 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.1983 | 1311.6 | -0.5338 | 1998.7 |

## Headline finding

The naive evaluation gives R² = 1.000 and is invalid (`casual + registered == cnt`). Under a temporal split (train 2011, valid H1 2012, test H2 2012), the mean baseline scores -2.1441 on test because ridership grew about 65% and the distribution moved. Persistence ("yesterday again") reaches 0.5099, ridge 0.5833 (a gain of 0.0734 R² that is lost on MAE: 947.1 vs 840.1), and gradient boosting -0.4975, negative but still far above the mean baseline, because a tree cannot predict above the 2011 maximum (6,043 rides) and 56.5% of test days exceed it. My feature `cnt_roll_3` lowered validation R² by 0.0036 (ridge) and 0.0202 (hgb), so I did not keep it as a model input: it is still built and tested, but listed in `REJECTED_FEATURES`.

## Exercise 4: target transformation

Validation first (`python -m src.transform_experiment`), on the final 14-feature set. hgb on validation: identity 0.2185, log target 0.1638, `cnt / cnt_roll_7` 0.7454 (ridge on identity: 0.6475). I picked the ratio target on validation and scored test once (`--test`): hgb 0.6416 (MAE 810.1), against ridge 0.5833 and persistence 0.5099 (MAE 840.1). (Test was first scored when `cnt_roll_3` was still an input, giving hgb 0.6225; after rejecting the feature I re-scored once on the final feature set. The transform choice was made on validation both times and did not change.) Is it defensible? Partly. `cnt_roll_7` uses only earlier days, so there is no leakage, and predicting growth relative to last week removes exactly the trend the tree could not extrapolate. But it is close to winning the comparison by moving the baseline inside the target: the tree now predicts an adjustment around a lag-based anchor, ridge got worse with the same trick (valid 0.3881, test 0.0226), and the gain over ridge on test is 0.06 R² on one 182-day window. I would report it as an explanation of why the tree failed, not as the tree beating ridge. The committed metrics.json is the untransformed pipeline.

## Exercise 5: ridge vs persistence

Ridge beats persistence by 0.0734 test R² (0.5833 vs 0.5099) but is 12.7% worse on MAE (947.1 vs 840.1 rides), and it is closer to the truth than persistence on only 38.6% of test days: it wins on a few large misses, which R² weights heavily (squared error), and loses on typical days. Its two largest standardised coefficients are `cnt_roll_7` (567) and `cnt_lag_1` (362), so it is mostly a smoothed "recent demand" estimate. My argument: not worth deploying on this evidence. A 0.07 R² gain from one test window, with a worse typical error and a model that needs a feature pipeline, does not clear the bar over a one-line baseline; I would deploy persistence and revisit ridge with rolling-origin validation across more than one window.

## Attribution

Model: the code, tests, docs and this report were written by Claude Sonnet 5.5 driven through Claude Code (a hosted model, not the assignment's local Ollama qwen3.5:9b setup); I did not switch models during the build. The batch audit (`agent/audit.py`) used the local `qwen3.6:27b-mlx` via Ollama on this machine. No local model drove the seeded-fault edits, so the "turns to fix" counts in `docs/SEEDED_FAULTS.md` are one edit each.

Agent-generated: `cnt_roll_3` and its test; `REJECTED_FEATURES`; `test_every_raw_column_is_classified`, `CLASSIFIED_RAW_COLS`; the hash check; `test_weather_encoder_rejects_unknown_label`; `src/transform_experiment.py`; the `seed-fault` skill; docs/SEEDED_FAULTS.md, docs/DECISIONS.md additions and this report.

Decisions that are mine (each traces to a line in `docs/DECISIONS.md`): what to predict (`cnt`), what counts as leakage (the starter's FORBIDDEN sets, unchanged), the temporal split, both baselines, whether the answer is believable, and dropping `cnt_roll_3` because it lowered validation R². The feature choice, the allowlist design, and the Exercise 4/5 arguments were drafted by the agent and reviewed by me.
