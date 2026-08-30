# Scientific verification

`python -m pytest -q` includes a real HiGHS two-bus dispatch with a 100 MW load:
a 40 MW corridor requires 60 MW of backup at 100 currency units/MWh (cost 6000).
Increasing capacity to 70 MW lowers cost to 3000. Renewable curtailment and
backup dispatch are checked against these hand-derived values.

A two-period lossless, cyclic battery moves 50 MWh without creating energy.
Failed, infeasible and time-limited solver terminations are rejected before
downstream output calculations. Normal runs require both `ok` and `optimal`.

These analytical/consistency tests do not validate Dutch topology, corridor
ratings, market behaviour or contingency security. The existing N-1 output is
still a screening proxy, not explicit element-outage re-solves.

The default is 168 snapshots with synthetic profiles/topology assumptions.
Public-data annual benchmarks, exact environment locks, true contingency
evaluation and archived release bundles remain separate gates. No reference
result is updated merely because these tests were added.
