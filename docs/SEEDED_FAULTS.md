# Seeded faults (Exercise 2)

Method: each fault was a one-line edit committed on its own ("SEEDED FAULT n"), followed by a fix commit. The hook was run by piping the same PostToolUse JSON payload Claude Code sends (`{"tool_input":{"file_path":".../src/features.py"}}`) into `.claude/hooks/check_leakage.sh` with `CLAUDE_PROJECT_DIR` set; "hook exit=2" means the failure would be sent back to the agent. No local coding model drove these edits: I made them directly, so "turns to fix" below is turns of mine, not of an Ollama agent.

## Fault 1: a forbidden column added to `feature_columns`

Turns to fix: 1 (revert the one line). Caught by `test_no_forbidden_features`.

Exact change and outputs (verbatim; the hook runs `tests/test_leakage.py` only, as in the starter):

```text
@@ -83,7 +83,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in (FORBIDDEN - {"registered"})]
 
 
 if __name__ == "__main__":
=== make test
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_3', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 1.28s
make: *** [test] Error 1
=== hook
Leakage tests failed after editing /Users/jassy/Documents/ucsd/capstone/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7   cnt_roll_3
0   2011-01-10     10.0  WINTER  ...     134....142857  2183.333333
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571  2077.333333

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_3', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.34s
hook exit=2
```

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

Turns to fix: 1. Caught by `test_rolling_mean_excludes_today`.

Exact change and outputs (verbatim; the hook runs `tests/test_leakage.py` only, as in the starter):

```text
@@ -73,7 +73,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
     # Short-window momentum: mean of the 3 days before today (shift first).
     out["cnt_roll_3"] = out[TARGET].shift(1).rolling(3).mean()
 
=== make test
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.36s
make: *** [test] Error 1
=== hook
Leakage tests failed after editing /Users/jassy/Documents/ucsd/capstone/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 8 passed in 0.34s
hook exit=2
```

## Fault 3: the weather encoder's `raise` removed

**Finding: the starter suite did NOT catch this.** With the `raise` removed, `make test` printed `16 passed` and the hook exited 0, because no test ever feeds `encode_weather` an unseen label (the real data has only GOOD/MISTY/BAD). I wrote `test_weather_encoder_rejects_unknown_label` first (commit "Test that encode_weather raises on unseen labels"), then re-seeded. Turns to fix: 1.

Before the new test (starter behaviour): `16 passed`, `hook exit=0`.

After the new test, exact change and outputs (verbatim):

```text
@@ -26,8 +26,7 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+    pass
     return series.map(WEATHER_ORDER).astype(float)
 
 
=== make test
        """encode_weather must raise on an unseen label instead of mapping it to
        NaN, which a later dropna() would silently delete."""
        from src.features import encode_weather
    
>       with pytest.raises(ValueError, match="unmapped weather labels"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_label - Fa...
1 failed, 16 passed in 1.30s
make: *** [test] Error 1
=== hook
Leakage tests failed after editing /Users/jassy/Documents/ucsd/capstone/bikeshare-open/src/features.py:
........F                                                                [100%]
=================================== FAILURES ===================================
__________________ test_weather_encoder_rejects_unknown_label __________________

    def test_weather_encoder_rejects_unknown_label():
        """encode_weather must raise on an unseen label instead of mapping it to
        NaN, which a later dropna() would silently delete."""
        from src.features import encode_weather
    
>       with pytest.raises(ValueError, match="unmapped weather labels"):
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_label - Fa...
1 failed, 8 passed in 0.31s
hook exit=2
```

## Fault 4: `cp` into `data/raw/` from Bash (invisible to the PostToolUse hook)

What happened: `cp /tmp/tampered.csv data/raw/bike_daily.csv` (the last day's `cnt` doubled). The permission deny rules bind the Edit/Write *tools*, not `cp` inside Bash; the hook only fires on Edit|Write of `src/*.py`. Output verbatim:

```text
$ cp /tmp/tampered.csv data/raw/bike_daily.csv  (tamper: cnt doubled for 2012-12-31)
--- hook after the cp:
hook exit=0
--- make test (before fix):
1 failed, 16 passed in 1.33s
make: *** [test] Error 1
--- sha256:
5eeb01d8a718377f
```

That red test was luck: doubling `cnt` broke `test_leakage_identity_holds` (`casual + registered == cnt`). I re-ran the starter's suite (the commit before the fix) against a quieter tamper, `temp + 1.0` on every row: `17 passed`, nothing red. A silent edit to raw data is invisible to the starter.

What would catch it: a content hash of the raw file (alternatives: a PreToolUse hook on Bash that rejects writes under `data/raw/`; `chmod -w data/raw`; a Stop hook that runs `make test`). I implemented the hash check (the assignment's sha256 prefix `a6bed1577f6e4de5` in `src/config.py`, enforced by `test_raw_data_is_unmodified` and by `load_raw`, so `make data` and every stage refuse a modified file). With the check in place and the tampered file copied back in (verbatim, trimmed to the distinct lines; `load_raw` also raises, so 14 other tests error out):

```text
E       AssertionError: data/raw modified: sha256 5eeb01d8a718377f
FAILED tests/test_contract.py::test_raw_data_is_unmodified - AssertionError: ...
1 failed, 3 passed, 14 errors in 1.23s
$ make data
ValueError: data/raw/bike_daily.csv was modified (sha256 5eeb01d8a718377f)
make: *** [data] Error 1
```

Limits: this is a test, so it fires when tests run, not at the moment of the `cp`; a PreToolUse hook on Bash would fire earlier. It also does not stop deletion of the check itself.

## Related check: a new column in the raw CSV

Adding a `members` column (copy of `registered`) made `test_every_raw_column_is_classified` fail:

```text
feature_columns, which would admit any new numeric column). Anything else is unclassified and fails here, so a new
        unclassified = raw_cols - known
>       assert not unclassified, f"unclassified raw columns: {sorted(unclassified)}"
E       AssertionError: unclassified raw columns: ['members']
1 failed, 15 passed in 1.28s
```

My first version of that test passed with the column present, because it classified against `feature_columns()`, which admits any new numeric column. It now checks against the explicit `CLASSIFIED_RAW_COLS` allowlist in `src/config.py`.
