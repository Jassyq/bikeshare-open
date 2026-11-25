# Audit of a teammate's repository (Exercise 3)

**Repository audited:** https://github.com/MichaelLuo123/bikeshare-open
**Commit:** `f3ba4da5e628ea01e06dc4c7552b9e9af33731fd`. Everything since his starter commit `fef3c5a` was in scope.
**Date:** 2026-11-24

**How it was run:** I ran the `leakage-auditor` reviewer from `.claude/agents/leakage-auditor.md`, with its five checks and its "report only findings that change a number" rule, as a subagent in a fresh context.
- **Model:** Claude Sonnet 5.5 through Claude Code, not the local Ollama model. The reviewer is the same model as the author, but with no shared context.
- **Access:** read and run only on a clone of his repo, with this repo's pinned virtualenv. It was told not to edit anything.
- **Extra check:** I also asked it to verify that his committed `metrics.json` and `REPORT.md` table reproduce.

## Auditor output (verbatim)

> ## Leakage audit: `MichaelLuo123/bikeshare-open` @ `f3ba4da5e628ea01e06dc4c7552b9e9af33731fd` (diff `fef3c5a..HEAD`)
>
> **Verdict:** No findings. All five checks pass, and the committed numbers reproduce exactly. Nothing in the diff changes a number or invalidates a conclusion.
>
> Code changes covered by the diff: `src/config.py` (`LAG_WARMUP` 7→14, new `RAW_FEATURE_COLS`), `src/features.py` (new `cnt_roll_14`; `cnt_lag_7` and `cnt_roll_7` now hard-code 7 instead of using `LAG_WARMUP`), and new tests in `tests/test_contract.py` and `tests/test_leakage.py`. `src/train.py` and `data/raw/bike_daily.csv` did not change.
>
> Interpreter: `/Users/jassy/Documents/ucsd/capstone/bikeshare-open/.venv/bin/python`. `pytest tests -q` → `17 passed in 1.18s`.
>
> ### 1. Target leakage: PASS
> The feature set is `temp, atemp, hum, windspeed, dayofweek, is_weekend, is_holiday, is_workday, month_sin, month_cos, weather_severity, cnt_lag_1, cnt_lag_7, cnt_roll_7, cnt_roll_14`. None of these columns is in `FORBIDDEN` (`casual`, `registered`, `cnt`, `instant`, `yr`, `days_since_2011`, `cnt_2d_bfr`).
> - No pair of features sums to `cnt`: a brute-force pairwise `np.allclose(f[a]+f[b], f.cnt)` printed nothing.
> - In-sample OLS of `cnt` on all 15 features over all 700 rows gives R² = 0.8262, not ≈1.0, so no linear restatement of the target exists.
> - The highest feature/target correlation is `cnt_roll_7` at 0.842.
> - Every target-derived feature uses `.shift(≥1)` (`src/features.py:73-76`).
>
> ### 2. Temporal ordering: PASS
> - **Aggregations:** both rolling means call `.shift(1)` before `.rolling()` (`src/features.py:75-76`). I recomputed each feature independently from calendar dates, using only strictly earlier days. Mismatches on all 700 rows: `{'cnt_lag_1': 0, 'cnt_lag_7': 0, 'cnt_roll_7': 0, 'cnt_roll_14': 0}`.
> - **Split:** the split is by date (`src/train.py:61-67`). The data splits into train 2011-01-17..2011-12-31, valid 2012-01-01..2012-06-30 and test 2012-07-01..2012-12-31, with no overlap.
> - **Fitted transformers:** the only one is `StandardScaler`, inside `make_pipeline(StandardScaler(), Ridge())`, which is fit on `train[cols]` only (`src/train.py:81`). HGB's automatic early stopping is off below 10,000 samples (n_train = 334), so it never sees validation or test rows.
>
> ### 3. Calendar gaps: PASS
> `reindex_to_calendar` inserts the missing day 2011-03-10 as a NaN row before any shift. Every row was checked with the calendar-based recomputation in check 2 (0 mismatches). This includes the rows just after the gap and `cnt_lag_7`, which now uses a literal `shift(7)`. Raising `LAG_WARMUP` to 14 therefore did not turn `cnt_lag_7` into a 14-day lag.
>
> ### 4. Silent row loss: PASS
> Raw data has 728 rows and the feature table has 700, so 28 rows are lost. The bound in `tests/test_contract.py:46` is `LAG_WARMUP + LAG_WARMUP*missing_days` = 14 + 14×1 = 28, which is exact (`lost <= allowed` with equality). Any additional silent drop fails the test.
> - The lost dates are exactly the warm-up 2011-01-03..2011-01-16 and the 14 days after the gap, 2011-03-11..2011-03-24.
> - All 20 BAD-weather days survive (raw `{'GOOD': 463, 'MISTY': 245, 'BAD': 20}`, features `{'GOOD': 445, 'MISTY': 235, 'BAD': 20}`).
> - `encode_weather` raises on unknown labels, so its `.map()` cannot silently create NaNs. There is no `.merge()` anywhere.
> - The test's docstring is stale but has no numeric effect: lines 33-39 still say a gap costs "7 rows" and that the longest window is `cnt_roll_7`.
>
> ### 5. Unreported baseline: PASS
> `baseline_mean` (the training mean) and `baseline_persistence` (`cnt_lag_1`) appear next to ridge and HGB, for both valid and test, in `reports/metrics.json`. They also appear in both the "Before" and "After" blocks of the REPORT.md table and in the headline and Exercise 5 prose.
>
> ### Reproducibility: PASS
> - **Committed metrics:** `python -m src.features` (700 rows, 15 features) followed by `python -m src.train`, then `diff reports/metrics.json <copy of committed metrics.json>`, printed `IDENTICAL`.
> - **"Before" rows:** I extracted `git archive fef3c5a` with the same raw CSV and ran it in scratch. It gives n_train 348, mean −0.9318/2002.2 and −2.1441/2847.7, persistence 0.4507/900.6 and 0.5099/840.1, ridge 0.6475/832.9 and 0.5833/947.1, HGB 0.2185/1296.6 and −0.4975/1972.6. Every value matches the REPORT.md table.
> - **"After" rows:** these match `metrics.json` exactly.
> - **Prose claims, re-run on validation only:** the identical-row ablation (ridge 0.6434→0.6919, HGB 0.1713→0.1643) and Exercise 4 (residual target 0.6161/823.5, ratio target 0.7347/667.4) reproduce exactly. The derived differences are also correct: +0.1169, 0.0734, 30.8 rides and +0.0485.
>
> ### Findings
> None that change a number or invalidate a conclusion.
>
> Outside the five checks, two things could matter later:
> - The diff removes the `Write(./data/raw/**)` deny rule from `.claude/settings.json`. The raw CSV itself is unchanged in `fef3c5a..HEAD`, so no current number is affected.
> - The stale docstring in `tests/test_contract.py:33-39` (check 4) should be updated to say 14.

## My verdict

I agree with the auditor: nothing in Michael's repo changes a number. I didn't want to take that on faith, so I re-ran the parts that matter on his clone:
- `pytest` gives 17 passed.
- `python -m src.features` gives 700 rows and 15 features.
- Regenerating `reports/metrics.json` gives a file identical to the one he committed.

The stale docstring in `tests/test_contract.py:33-39` is real. It still says a missing day costs 7 rows when his `LAG_WARMUP` is now 14. But that's documentation, not a bug.

The one place I'd push harder than the auditor did is the removed `Write(./data/raw/**)` deny rule. It doesn't change any number today, since his raw CSV is untouched. But it means the agent can now overwrite the raw data with the Write tool, and nothing else in his repo checks the file's contents. If that ever happened, a tampered CSV would flow into every metric without a single test going red. I'd put the rule back and add a hash check on the raw file, which is what I ended up doing in my own repo after my `cp` fault.

The detail I was most impressed by is how he handled `LAG_WARMUP`. In the starter code, `cnt_lag_7` uses `shift(LAG_WARMUP)`. So raising `LAG_WARMUP` to 14 for his `cnt_roll_14` would have quietly turned it into a 14-day lag. He hard-coded the 7 instead, and the auditor's recomputation from calendar dates found all four lag features correct. Overall, I find his results believable as reported.
