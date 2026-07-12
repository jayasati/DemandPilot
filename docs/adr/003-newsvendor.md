# 003. Use the newsvendor model for inventory optimization

## Status

Accepted

## Context

The stocking decision per store/SKU/period is: order quantity `Q` under
uncertain demand, where overstock costs `Co` per unit (unrecovered cost +
holding) and understock costs `Cu` per unit (lost margin + goodwill). This is
the classic single-period newsvendor problem with the closed-form optimum
`Q* = F⁻¹(Cu / (Cu + Co))` — the demand quantile at the critical fractile.
Alternatives (multi-period (s,S) policies, stochastic programming) need
lead-time demand processes and state that M5 doesn't provide, and would bury
the forecast→decision link the platform exists to demonstrate.

## Decision

The newsvendor model translates probabilistic forecasts into order quantities.
`Q*` is read directly from the forecast quantile at the critical fractile
implied by `configs/costs.yaml` (ADR-012). Implementation: pure math in
`demandpilot.core.newsvendor` (critical fractile landed in Volume 0; the full
policy lands in Volume 4).

## Consequences

- Closed-form, explainable, and probabilistic by construction — it consumes
  the quantile forecasts natively; asymmetric costs are first-class.
- Single-period assumption: no inventory carryover or lead-time aggregation in
  the first cut; (s,S)/multi-echelon are future extensions
  (docs/KNOWN_LIMITATIONS.md). The simulation engine (Volume 5) quantifies how
  much this simplification costs.
