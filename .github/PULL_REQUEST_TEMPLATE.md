# Summary

<!-- What does this PR do, and why? Link the roadmap volume or issue. -->

## Checklist (Definition of Done — docs/DEFINITION_OF_DONE.md)

- [ ] Follows the volume lifecycle: planning → architecture → implementation → testing → review → audit → documentation → merge
- [ ] All public functions have type hints, docstrings, and logging where meaningful
- [ ] Unit/integration tests added or updated; `poe check` passes locally
- [ ] No hardcoded paths or configuration; everything flows through `configs/`
- [ ] SQL lives in `sql/`, not in Python strings
- [ ] Docs updated (ARCHITECTURE / DATA_MODEL / ADRs / CHANGELOG as applicable)
- [ ] No fake data, fake metrics, placeholder implementations, or TODO functions
