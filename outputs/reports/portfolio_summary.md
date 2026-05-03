# Portfolio Summary

## Problem Statement

The project screens grid-flexibility options for a simplified Netherlands-inspired constrained grid. It compares renewable growth, storage siting, flexible connection logic and targeted reinforcement using a reproducible PyPSA workflow.

## Methodology

- Build regional PyPSA networks from transparent configuration assumptions.
- Solve hourly linear dispatch for each scenario with HiGHS.
- Export scenario KPIs, hourly dispatch, bottleneck diagnostics and BESS sweep results.
- Validate KPI consistency before writing reports.
- Interpret results through a multi-KPI grid-value score instead of a single curtailment metric.

## Latest Key Findings

- Top-ranked scenario: **High Wind Offshore Growth** with grid-value score **60.8**.
- It adds **201,561 MWh** of renewable dispatch and reduces backup generation by **201,561 MWh** versus base.
- Congestion-cost proxy is reduced by **EUR 7,984,655** versus base.
- Absolute curtailment is **higher** than base by **170,594 MWh**, so the ranking should be read as a multi-KPI trade-off rather than a curtailment-only result.
- Base case curtailment is **484,638 MWh** at **24.4%**.
- Best BESS sweep option: **Groningen 400 MW / 4 h**, with score **8.9**.
- Validation checks passed: **8/8**.

## Validation

- Failed validation checks: **none**
- The validation layer checks solver status, curtailment balance, percentage bounds, BESS-cycle sanity, objective costs and rank completeness.

## Limitations

- The network is a simplified regional proxy, not a validated Dutch transmission model.
- The congestion-cost metric is a screening proxy, not an LMP or market settlement price.
- Profile shapes, line ratings and congestion windows are transparent modelling assumptions.
- BESS business-case values exclude degradation, revenue stacking and detailed financing.

## Next Improvements With Production Data

- Replace proxy topology with validated grid zones and corridor limits.
- Use audited hourly load, wind, solar and offshore production profiles.
- Add contingency-constrained flows or explicit post-contingency screening.
- Extend BESS economics with degradation, reserve markets and imbalance-market revenue.
- Calibrate congestion-cost proxies against observed redispatch or constraint-management costs.
