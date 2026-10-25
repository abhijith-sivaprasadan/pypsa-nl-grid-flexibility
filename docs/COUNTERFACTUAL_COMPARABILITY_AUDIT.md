# Counterfactual comparability screen: saved PyPSA scenarios

The committed nine scenarios are **stylised synthetic-network** PyPSA
optimisations. An optimal solver status does not authenticate a Dutch line
limit, congestion window, national/municipal allocation, or market price.

The analysis contains a specific confound: the flexible-connection and
combined flexible-storage scenarios serve *different configured demand* from
the reference, so their total objective costs are not a strict fixed-service
comparison with the reference. It is legitimate to report their simulation
results, but not to interpret an unnormalised aggregate cost delta as the
effect of a single intervention holding demand constant.

The auditable command:

```bash
python scripts/audit_counterfactuals.py
pytest -q tests/test_counterfactual_comparability.py
```

recomputes the demand balance, renewable availability/dispatch/curtailment
balance, and like-for-like **demand** membership from the committed
`outputs/tables/scenario_summary.csv`. It fails on changed balances,
non-optimal solver statuses and duplicate names. This is an arithmetic audit
of published aggregates, **not** a re-solve against the hourly CSV,
field-measurement validation or upstream dataset authentication.

Matching total demand is a necessary but not sufficient condition for a
fixed-service comparison. Wind/solar expansion intentionally changes resource
availability, while other interventions change capacity or operating
constraints. These scenarios remain controlled *synthetic* counterfactuals,
not estimates of true Dutch electricity-system benefits.

Next science gate: add independent hourly source data, explicit year/time
coverage and an input-manifest checksum; then repeat dispatch with pinned
observed chronology and clearly stated network reconstruction assumptions.
A provincial topology based on simplified corridors does not become
operator-grade merely by receiving an observed demand time series.
