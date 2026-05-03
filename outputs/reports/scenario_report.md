# PyPSA-NL Grid Flexibility Scenario Report

This automated report summarises the synthetic PyPSA scenario run for grid congestion, connection capacity, BESS and flexible contracts.

## Top scenarios by decision-support score

| scenario                  |   renewable_dispatch_increase_vs_base_mwh |   backup_reduction_vs_base_mwh |   line_overload_reduction_vs_base_hours |   total_congestion_cost_proxy_eur |   grid_value_score |
|:--------------------------|------------------------------------------:|-------------------------------:|----------------------------------------:|----------------------------------:|-------------------:|
| high_wind_offshore_growth |                                   63480.4 |                        63480.4 |                                    -172 |                       4.18073e+07 |              39.47 |
| combined_bess_and_flex    |                                   53479.6 |                        51054.8 |                                     -64 |                       4.62496e+07 |              30.65 |
| bess_noord_brabant        |                                   28097.1 |                        26283.5 |                                      37 |                       4.30986e+07 |              24.13 |
| bess_noord_holland        |                                   28322.5 |                        26424.4 |                                       3 |                       4.35771e+07 |              20.33 |
| bess_flevoland            |                                   27997.8 |                        26165.3 |                                       3 |                       4.36293e+07 |              19.97 |

## Interpretation guide

- High-renewable scenarios can increase absolute curtailment because renewable availability rises faster than grid capacity.
- The grid-value score therefore combines renewable dispatch, backup reduction, line-overload relief, curtailment-rate change, objective cost and congestion-cost proxy.
- The congestion-cost proxy combines curtailment value loss, backup generation cost and line-hours above the utilisation threshold.

## BESS siting and sizing top options

| bess_region   |   bess_power_mw |   bess_duration_h |   backup_reduction_mwh |   renewable_dispatch_gain_mwh |   line_overload_reduction_hours |   sweep_grid_value_score |
|:--------------|----------------:|------------------:|-----------------------:|------------------------------:|--------------------------------:|-------------------------:|
| Noord-Brabant |             400 |                 4 |                11035.1 |                       12488.8 |                              21 |                    90.46 |
| Groningen     |             400 |                 4 |                11112.2 |                       12638   |                              19 |                    89.87 |
| Zuid-Holland  |             400 |                 4 |                11150.4 |                       12706.5 |                              15 |                    87.62 |
| Zeeland       |             400 |                 4 |                10872.5 |                       12380.6 |                              10 |                    82.41 |
| Noord-Holland |             400 |                 4 |                11219.7 |                       12758   |                              -2 |                    77.02 |

## Generated figures

- E:\pypsa_nl_grid_flexibility_platform_FINAL\pypsa_nl_grid_flexibility_platform\outputs\figures\grid_value_score_by_scenario.png
- E:\pypsa_nl_grid_flexibility_platform_FINAL\pypsa_nl_grid_flexibility_platform\outputs\figures\congestion_cost_proxy_by_scenario.png
- E:\pypsa_nl_grid_flexibility_platform_FINAL\pypsa_nl_grid_flexibility_platform\outputs\figures\bess_siting_sizing_score.png
- E:\pypsa_nl_grid_flexibility_platform_FINAL\pypsa_nl_grid_flexibility_platform\outputs\figures\network_diagram.png

## Scope note

This is a portfolio model using synthetic data. It demonstrates workflow and modelling capability, not an operational Dutch grid study.