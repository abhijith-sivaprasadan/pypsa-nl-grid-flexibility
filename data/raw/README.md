This project uses public Dutch statistics for model calibration and transparent
proxy profiles for hourly operation.

Current sourced calibration inputs:

- National electricity use: Compendium voor de Leefomgeving/CBS reports Dutch
  electricity consumption of about 116 billion kWh in 2023. The regional demand
  bases in `config/model_config.yaml` are scaled so the model's annualised
  demand level is in that range.
- Renewable capacity totals: CBS StatLine 82610ENG reports 2024 revised
  provisional installed capacity of 24,772 MW solar PV, 6,955 MW onshore wind
  and 4,748 MW offshore wind.
- Provincial renewable allocation: CBS Netherlands in Numbers 2023 gives 2022
  provincial installed solar and onshore wind capacity. Those provincial shares
  are scaled to the CBS 2024 national totals.
- Optional hourly profile source: Open Power System Data `time_series`
  60-minute single-index file includes Netherlands load, solar, wind and
  offshore wind columns derived from ENTSO-E Transparency data.

Simplifications kept intentionally:

- Hourly demand, solar, onshore wind and offshore wind profiles are generated
  by transparent deterministic proxy functions in `profiles.py`.
- To use OPSD hourly profiles instead, run:

```bash
python scripts/download_opsd_profiles.py
```

Then set `model.profile_source: "opsd"` in `config/model_config.yaml`.
The model will read `data/raw/opsd_time_series_60min_singleindex.csv` and
normalise these trusted Netherlands time series into profile shapes.

- If the OPSD file is not present and `profile_source` is left as `"proxy"`,
  the project remains self-contained and uses the deterministic proxy profiles.
- Inter-regional grid corridors and line ratings are simplified assumptions,
  not validated TenneT network data.
- Congestion-cost and line-overload values are decision-support proxy metrics,
  not market-clearing prices or redispatch settlement costs.
