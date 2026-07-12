# 004. Use Streamlit for the app/UI layer

## Status

Accepted

## Context

The dashboard is an internal decision-support tool for planners: browse
forecasts, recommendations, and simulation results. Needs: Python-native
(reuse the package directly), fast iteration, Plotly support. A separate
frontend (React + API) would multiply the stack for an audience of analysts;
Dash offers more layout control at the cost of significantly more boilerplate.

## Decision

Streamlit, as a pure presentation layer: pages call the application layer and
render results; zero business logic in the app. Reads via read-only DuckDB
connections (ADR-001). Binds 127.0.0.1 in dev, 0.0.0.0 only in the container.

## Consequences

- A working dashboard in days, in the same language and package as the pipeline.
- Rerun-the-script execution model demands caching discipline
  (`st.cache_data`) around DuckDB reads; limited fine-grained UI control —
  accepted for an internal tool.
- If requirements outgrow it (auth, multi-user state), the clean layering
  keeps a swap to Dash/FastAPI+frontend contained in the presentation layer.
