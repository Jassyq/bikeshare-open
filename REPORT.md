# Report: forecasting bikeshare demand with an agent

## Results

The table compares the pipeline with and without the feature I tried, `cnt_roll_3`, the average ride count over the three days before each date. "Before" is the pipeline without it, 14 features. That is also my final pipeline, so these rows are exactly what `make all` writes to `reports/metrics.json`, and they match the starter's numbers (`reports/metrics_starter.json`). "After" is the same pipeline with `cnt_roll_3` added as a 15th input, saved in `reports/metrics_with_cnt_roll_3.json`. I ended up dropping the feature, which is why the committed metrics are the "before" rows.

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

If you ask for a model in the most obvious way, you get R² = 1.000. That number is worthless: `casual + registered` adds up to `cnt` exactly, so the model has learned addition, not forecasting. Once the split respects time (train on 2011, validate on the first half of 2012, test on the second half), the picture looks very different. The mean baseline scores -2.1441 on test because ridership grew about 65% between the two years, so the 2011 average is badly off for late 2012. Persistence, which predicts yesterday's count, gets 0.5099. Ridge gets 0.5833, which is 0.0734 better in R² but worse in MAE (947.1 vs 840.1). Gradient boosting comes in at -0.4975. That is negative, but still well above the mean baseline. The reason it fails is that a tree can't predict above the highest value it saw in training, the 2011 maximum of 6,043 rides, and 56.5% of test days are above that. The feature I added, `cnt_roll_3`, made validation R² slightly worse for both models: -0.0036 for ridge and -0.0202 for hgb. So I dropped it as a model input. I kept the code and its test, and listed it in `REJECTED_FEATURES` so the decision is visible.

## Exercise 4: target transformation

I wanted to see whether the tree could compete if it didn't have to extrapolate the growth trend. I tried three targets on validation only (`python -m src.transform_experiment`):
- the raw count: hgb gets 0.2185
- the log of the count: 0.1638, slightly worse
- the count divided by the previous week's average, `cnt / cnt_roll_7`: 0.7454

The ratio target jumped well past ridge's 0.6475 on validation. I chose it based on that and then scored the test set once (`--test`): hgb reached 0.6416 (MAE 810.1), compared with ridge at 0.5833 and persistence at 0.5099 (MAE 840.1).

To be transparent about the test set: I first scored it while `cnt_roll_3` was still an input, which gave hgb 0.6225. After I dropped that feature I scored it once more on the final feature set. Both times the transform was chosen on validation, and the choice didn't change.

Is this transformation defensible, or just a way to win the comparison? I think it's partly both.
- **Why it's legitimate:** `cnt_roll_7` only uses earlier days, so nothing leaks. Predicting "how does today compare to last week" removes exactly the trend the tree couldn't handle.
- **Why I'm cautious:** dividing by last week's average moves a persistence-style baseline inside the target. The tree is now predicting a small adjustment around a number that already does most of the work.
- **It doesn't generalise:** ridge got much worse with the same trick (0.3881 on validation, 0.0226 on test).
- **The margin is small:** the tree's lead over ridge on test is only 0.06 R², from a single 182-day window.

So I'd present this as an explanation of why the tree failed, not as evidence that the tree is the better model. The committed `metrics.json` uses the plain, untransformed pipeline.

## Exercise 5: ridge vs persistence

I don't think ridge is worth deploying over "yesterday again", at least not on this evidence. On paper ridge wins: test R² 0.5833 against 0.5099, a gap of 0.0734. But its average error is 12.7% worse (947.1 vs 840.1 rides). It also gets closer to the true count than persistence on only 38.6% of test days. Those two facts together tell me ridge wins R² by avoiding a few large misses, which R² punishes heavily because it squares the errors, while doing worse on a typical day. Looking at ridge's standardised coefficients, the two biggest are `cnt_roll_7` (567) and `cnt_lag_1` (362). It is mostly a smoothed version of recent demand, not something that understands much beyond that. A 0.07 R² gain on one test window, a worse typical error, and a feature pipeline to maintain don't add up to a reason to replace a one-line baseline. I'd ship persistence for now and come back to ridge with rolling-origin validation over several windows, so the comparison isn't resting on one half-year.

## Attribution

**Model used:** Claude Sonnet 5.5 through Claude Code, a hosted model, not the assignment's suggested local Ollama setup (qwen3.5:9b). I didn't switch models during the build. The batch audit in `agent/audit.py` ran on the local `qwen3.6:27b-mlx` through Ollama on my machine. No local model drove the seeded-fault edits, so the "turns to fix" counts in `docs/SEEDED_FAULTS.md` are one edit each.

**What the agent generated:**
- `cnt_roll_3` and its test
- `REJECTED_FEATURES`
- `test_every_raw_column_is_classified` and `CLASSIFIED_RAW_COLS`
- the raw-data hash check
- `test_weather_encoder_rejects_unknown_label`
- `src/transform_experiment.py`
- the `seed-fault` skill
- `docs/SEEDED_FAULTS.md`
- the additions to `docs/DECISIONS.md`
- the text of this report, drafted by the agent and revised at my direction

**What I decided** (each traces to a line in `docs/DECISIONS.md`):
- predicting `cnt`
- treating the starter's `FORBIDDEN` columns as the definition of leakage
- the temporal split and the two baselines
- whether the results are believable
- dropping `cnt_roll_3` because it lowered validation R²
- where I come down on Exercises 4 and 5: the transformation explains the tree's failure but doesn't make it the better model, and persistence is the safer thing to deploy
