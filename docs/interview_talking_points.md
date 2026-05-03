# Interview Talking Points

## Why this project is relevant
It directly maps to grid-flow modelling work: congestion, connection capacity, curtailment, BESS, renewables, flexible contracts and decision-support outputs.

## What was added beyond a toy model
- Scenario-driven PyPSA workflow
- Multi-region Netherlands-inspired topology
- BESS siting and sizing sweep
- Explicit flexible-connection logic
- Congestion-cost proxy
- Streamlit dashboard
- Executive reports and plots

## Key modelling insight
Absolute curtailment alone is not enough. High-renewable scenarios can have more curtailment but still reduce backup generation and emissions. That is why the score combines multiple KPIs.

## Limitations
Synthetic grid, synthetic profiles, no formal market model, no TSO-grade validation.
