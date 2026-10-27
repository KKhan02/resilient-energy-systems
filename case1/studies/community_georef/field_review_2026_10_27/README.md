# El Arenal Case 1: field-reviewed points and candidate EPM supply areas (27 Oct 2026)

**Source-only evidence update. No electrical topology, inverter dispatch, field-surveyed drops or pandapower run is asserted.**

This directory is an overlay on the original 35 point IDs from the already-merged Case 1 GIS study. It does not replace or rewrite the affine registration source, the historical 35-location screenshot, or the original georeferencing QA dataset.

## Changes

- All 35 positions preserved. 19 user-refined mapped positions, 5 previously supplied landmark points (H05 tentative), 11 retained prior estimates.
- 6 existing EPM transformer **nodes** (not six invented transformers). An additional previously supplied north 25 kVA transformer has unconfirmed node/asset number.
- H12 → 900607, H17 → 923494, H30 → 923848 recorded as **user definite**, meaning confidence in the EPM viewer interpretation, **not independent customer-service certification**. Other links are probable, possible, alternative, unverifiable or unknown.
- H10 could be behind 923494 or 823002; H29 behind 931076 or 923848. H01 and H02 have no single new assigned source (earlier H02 hypothesis: 931076 or northern 25 kVA).
- All geographic positions and associations come from user's latest reviewed table; retained prior coordinates have NOT been independently verified as surveyed meter connections.

## EPM identifiers and ratings

Do NOT conflate `Nodo Transformador` with `No. Transformador`. In particular, node **923848** → number **92395**, and node **931076** → number **94022**. Duplicate screenshot columns were deduplicated. The supplied portal table labels capacities as **Capacidad Nominal [kW]**, so 3 kW or 5 kW is **not assumed to be 3 kVA or 5 kVA**. Separate historical 5 kVA ratings for transformer 92395 and 94022 retain their original source context. The north 25 kVA asset is from the previous 2026-10-26 EPM record, location 6.249940251,-75.011914005.

Five new portal record columns say Municipio **SAN CARLOS** even though this study concerns El Arenal, San Rafael. The source's two-decimal coordinate display is unsuitable for locating the transformer poles. Both ambiguities must remain open until cross-checked in EPM.

The official viewer is https://maps.epm.com.co/ETER/Visor/Visor . The line symbol described by the user matches several **DISEÑO** categories, including subterranean and facade/aerial types. Visually mapped design lines are not proof of as-built, energized connections. The 221-12 vs 221-13 circuit distinction is retained.

## Outputs

- `houses_field_review.csv`: 35 ID-only locations, per-house provenance, positional change relative to original affine estimate, and source-scoped transformer candidates.
- `houses_field_review.geojson`: current geographic feature layer, with neither private-person names nor asserted electrical service allocations.
- `epm_transformer_register.csv`: 6 unique node/number pairs plus separate 25 kVA northern candidate, with exact unit labels and source provenance.
- `review_findings.json`: machine-readable counts, exceptions and limitations.
- `test_field_review.py`: source-only QA that rebuilds and checks CSV/GeoJSON consistency, deduplication, ambiguous assignment, no invented transformer kVA and no unverified feeder connections.

## Next engineering step

The feasible physical modelling comparison needs **separate existing LV service areas**, not one 35-house network behind 94022. The reference v5 5 kVA, 324.5 m representative feeder remains a controlled historical baseline, not the verified lines of H01-H35. Do not run or claim a real network until source constraints are resolved or clearly conditional alternative assignment scenarios are selected. Once ready, study central vs multiple SHARED PV+BESS clusters with matched total kWp, kWh, kW, curtailment/export limits and peak-shaving sensitivity. Keep new transformer additions exceptional and costed. Park critical/deferrable load shares completely.
