# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-21: Added `cnt_roll_3` (mean of the 3 days before today). Availability: every input is a count from a strictly earlier day, so it is known at prediction time. Validation R^2 ridge 0.6475 -> 0.6439 (-0.0036), hgb 0.2185 -> 0.1983 (-0.0202); both below the skill's 0.01 bar, so the skill's rule says drop it. Recorded as a null result.
- 2026-11-21: Allowlist the raw columns (`CLASSIFIED_RAW_COLS`) rather than deriving "known" from `feature_columns()`. A denylist-derived check admits a new numeric column silently, which my first version of the test did; it now fails on an unclassified column.
- 2026-11-21: Added `test_weather_encoder_rejects_unknown_label` after seeding fault 3 showed the starter suite stayed green with the encoder's `raise` removed.
- 2026-11-21: Raw data guarded by a sha256 prefix (`RAW_SHA256_PREFIX`) in `load_raw` and `test_raw_data_is_unmodified`, because a `cp` from Bash bypasses the Edit/Write deny rules and a quiet edit (`temp + 1`) passed the starter's whole suite.
- 2026-11-21: Exercise 4 transformation: predict `cnt / cnt_roll_7` and multiply back. Chosen on validation (hgb 0.1983 -> 0.7483; log target 0.1617 did not help); test scored once: hgb 0.6225 vs ridge 0.58. Defensible rather than a trick: `cnt_roll_7` is built from earlier days only, so no leakage, and the target becomes "growth relative to last week", which removes the trend the tree could not extrapolate. But it is not free: it makes the tree an adjustment around a lag-based anchor, ridge got much worse under it (valid 0.3924), and hgb at 0.6225 sits only 0.04 above ridge. Re-scored on test once more after dropping `cnt_roll_3` (final feature set): hgb 0.6416 vs ridge 0.5833; transform choice unchanged. Code in `src/transform_experiment.py`, not in `make all`; committed metrics.json is the untransformed pipeline.
- 2026-11-21: CLAUDE.md: added the `seed-fault` skill and the raw-data hash rule; removed nothing.
- 2026-11-24: Dropped `cnt_roll_3` as a model input because it lowered validation R^2 (ridge -0.0036, hgb -0.0202). It stays built and tested but is listed in `REJECTED_FEATURES` (src/config.py), so `metrics.json` is back to the 14-feature numbers; the with-feature run is kept in `reports/metrics_with_cnt_roll_3.json`.
