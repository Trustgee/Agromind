
# Thesis-ready model notes

Agromind's AOSIS v14 physics engine was used as the labelling authority. The physics engine incorporates clay-loam soil water storage, crop root-zone parameters, crop coefficients, forecast rainfall over a 48-hour horizon, recovery constraints and a maximum practical application depth.

The machine-learning stage uses two Gradient Boosting models:

1. A classifier for irrigation need: LOW, MEDIUM and HIGH.
2. A regressor for recommended daily irrigation depth.

A LOW prediction is gated to exactly zero irrigation. For MEDIUM and HIGH states, the regressor predicts application depth and the final output is bounded by the 12 mm/day practical application limit.

Water volume and pump runtime are calculated after inference rather than independently learned, maintaining physical consistency with farm area, application efficiency and pump flow.
