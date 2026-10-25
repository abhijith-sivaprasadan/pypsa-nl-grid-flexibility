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

All six cases are compared on **identical 168 UTC hours, from 2019-10-24
08:00 UTC to 2019-10-31 07:00 UTC**. This is the first complete 2019 source
window selected by the fixed, result-independent completeness rule, not
January 1–7 or a random/representative sample. and the same configured baseline demand and technology
portfolio within the relevant scenario pair. Each model is solved again under
each line factor. The output includes original file SHA-256, selected date
range, source-data role and numerical KPIs. No posterior tuning, external
grid-calibration, verified corridor data or investor-cost attribution.

## Completed observed-shaped reoptimisation evidence

[GitHub Actions run 40246133148](https://github.com/abhijith-sivaprasadan/pypsa-nl-grid-flexibility/actions/runs/40246133148) passed and uploaded artifact `observed-2019-synthetic-grid-sensitivity`, containing `manifest.json` and `six_solved_scenarios.csv`. Original OPSD file byte count: 130,339,665; SHA-256 `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`.

| Portfolio | Line rating multiplier | Modeled backup MWh | Renewable curtailment MWh |
|---|---:|---:|---:|
| Baseline capacities | 0.75x | 1,059,541.30 | 92,024.06 |
| Baseline capacities | 1.00x | 1,039,768.92 | 72,251.68 |
| Baseline capacities | 1.25x | 1,025,773.35 | 58,256.11 |
| Expanded wind | 0.75x | 899,472.45 | 303,335.55 |
| Expanded wind | 1.00x | 851,029.60 | 254,892.70 |
| Expanded wind | 1.25x | 819,460.19 | 223,323.30 |

These are modeled values with hypothetical network ratings, simplified regional demand and historical generated-power *shapes*; they are not metered Dutch curtailment or actual load shedding.
