# Methodology

## Objective

The objective is to demonstrate a grid-flow modelling workflow relevant to renewable developers, BESS developers, investors and strategic energy studies.

The model answers questions such as:

- Where do bottlenecks appear?
- How much renewable energy is curtailed?
- Does storage reduce curtailment or merely shift congestion?
- Which candidate BESS location gives the best grid value?
- How does grid reinforcement compare with flexibility?
- What happens when flexible connection constraints are imposed?

## Model type

The model uses PyPSA to solve an hourly linear optimal power-flow style dispatch problem on a synthetic regional network.

## Why PyPSA?

PyPSA is suitable for this portfolio because it supports networks, generators, storage, time-series optimisation and line-flow constraints in a reproducible Python workflow.

## Synthetic data

All data is synthetic. The model is intentionally not a real Dutch network model. It is structured to demonstrate modelling capability while avoiding false claims about operational validity.

## Decision-support logic

The most important outputs are not only dispatch plots. The workflow translates model results into decision-support KPIs:

- curtailment avoided
- backup avoided
- line loading reduced
- storage utilisation
- flexibility value proxy
- emissions proxy
- grid value score
