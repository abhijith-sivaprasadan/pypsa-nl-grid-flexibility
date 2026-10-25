# Registered observed-shaped Dutch grid sensitivity

The default model is an explicitly synthetic Dutch provincial testbed. This
separate and non-destructive experiment makes a **strict exact-hour** replacement
for the model's synthetic load/generation chronology using the public OPSD
2020-10-06 release's Dutch 2019 hourly observations, then re-solves six
scenarios with 0.75×, 1.0× and 1.25× **synthetic** corridor ratings under
unchanged model definitions.

Raw data: https://doi.org/10.25832/time_series/2020-10-06.
The source timestamp MUST match the requested UTC hour; the old loader read
the file's first N rows even if a different year was configured. We now fail
closed on absent inputs, duplicated hours and missing measurements. Wind
onshore and offshore are kept distinct.

The source provides historical **generation**, not unconstrained meteorological
*availability*. The inherited modelling assumption normalises generation by
each source channel's maximum to form a shape, then applies the project's
hypothetical 2024 regional capacities. Do not interpret these results as
a reconstructed actual 2019 grid or as a validated forecast for 2026.

Run:
```bash
python scripts/download_opsd_profiles.py
python scripts/run_observed_line_sensitivity.py
```

All six cases are compared on **identical 168 UTC hours, 2019-01-01 to
2019-01-07 inclusive** and the same configured baseline demand and technology
portfolio within the relevant scenario pair. Each model is solved again under
each line factor. The output includes original file SHA-256, selected date
range, source-data role and numerical KPIs. No posterior tuning, external
grid-calibration, verified corridor data or investor-cost attribution.
