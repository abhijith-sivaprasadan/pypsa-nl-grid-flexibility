# Assumptions and Limitations

## Assumptions

- Regional buses are stylised Dutch provinces / offshore injection nodes.
- Transmission capacities are synthetic and deliberately constrained.
- Demand scale is calibrated to public Dutch electricity-use statistics.
- Solar PV, onshore wind and offshore wind installed capacity are calibrated from CBS public renewable-capacity statistics.
- Provincial solar and onshore wind allocations use CBS provincial installed-capacity shares, scaled to the selected national capacity year.
- Hourly demand, wind and solar profiles are transparent proxy shapes designed to produce plausible daily and weather-driven variation.
- Backup generators represent imports, gas generation or local system balancing.
- BESS operation is optimised for system cost, not revenue stacking.
- Flexible connection logic is represented through capped renewable availability during recurring congestion windows.

## Limitations

- No real TSO/DSO line-by-line grid data is used.
- No AC power-flow validation is performed.
- N-1 output is a post-processing screening proxy from solved line flows, not a full contingency re-dispatch or AC security assessment.
- No reactive power or voltage constraints are modelled.
- No electricity-market bidding strategy is implemented.
- No battery degradation model is included.
- No real location-specific weather data is included.
- Regional demand allocation remains a proxy; the national total is calibrated, but provincial load is not claimed as official metered demand.

## Why this is still useful

For a job application, the project demonstrates:

- PyPSA model construction,
- scenario design,
- grid-flow constraint thinking,
- congestion and curtailment analysis,
- BESS siting logic,
- reproducible outputs,
- communication of modelling assumptions.
