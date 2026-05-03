# Executive Grid Flexibility Report

## Purpose

This project evaluates Netherlands-inspired grid congestion scenarios using PyPSA. It focuses on connection-capacity constraints, renewable curtailment, BESS siting, flexible connection logic and a congestion-cost proxy for decision support.

## Main scenario result

- Top-ranked scenario: **High Wind Offshore Growth**
- Decision-support score: **60.8**
- Renewable dispatch increase vs base: **201,561 MWh**
- Backup reduction vs base: **201,561 MWh**
- Emissions reduction vs base: **84,656 tCO2**
- Congestion-cost proxy change vs base: **EUR 7,984,655**

## Why absolute curtailment is not enough

High-renewable scenarios can increase absolute curtailment because renewable availability rises faster than grid capacity. The ranking therefore combines renewable dispatch, backup reduction, line-overload relief, curtailment-rate change, system cost and congestion-cost proxy.

## Dynamic key findings

- Top-ranked scenario: **High Wind Offshore Growth** with grid-value score **60.8**.
- It adds **201,561 MWh** of renewable dispatch and reduces backup generation by **201,561 MWh** versus base.
- Congestion-cost proxy is reduced by **EUR 7,984,655** versus base.
- Absolute curtailment is **higher** than base by **170,594 MWh**, so the ranking should be read as a multi-KPI trade-off rather than a curtailment-only result.
- Base case curtailment is **484,638 MWh** at **24.4%**.
- Best BESS sweep option: **Groningen 400 MW / 4 h**, with score **8.9**.
- Validation checks passed: **8/8**.

## Base-case reference

- Base renewable share of demand: **67.3%**
- Base backup dispatch: **727,130 MWh**
- Base line-hours above 90% utilisation: **775**
- Base congestion-cost proxy: **EUR 112,203,848**

## Validation summary

- Validation checks passed: **8/8**
- Failed checks: **none**

The validation layer checks solver status, curtailment balance, percentage bounds, BESS-cycle sanity and recommendation-rank completeness before the report is written.

## BESS siting and sizing result

- Top BESS option: **Groningen — 400 MW / 4 h**
- BESS score: **8.9**
- Backup reduction: **10,617 MWh**
- Renewable dispatch gain: **12,105 MWh**
- Congestion-cost reduction: **EUR 1,900,472**

The BESS sweep compares candidate locations, power ratings and durations. The best option is not necessarily the largest battery; it is the option with the best combination of renewable-dispatch gain, backup reduction, congestion-cost relief and utilisation per MW/MWh of battery capacity.

## Modelling limitations

- The grid topology and time series are synthetic and intended for portfolio demonstration.
- The congestion-cost proxy is not a formal market price or locational marginal price.
- The model is designed for scenario screening and communication, not TSO-grade planning.
