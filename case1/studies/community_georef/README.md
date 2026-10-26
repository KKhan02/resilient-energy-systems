# San Rafael Case 1: provisional property GIS and EPM infrastructure overlay

**Research screen only. No field-surveyed positions, transformer service territories, or verified 33-house customer roster.**

Original satellite image and 35 x/y points are reused from `Energy Community - San Rafael/SanRafael_Reproducible_Model_Package_v2/`. No re-digitizing, new transformers, or feeder mapping is asserted.

## User-approved coordinates (26 Oct 2026)

Five registration points: H1 (Ashram), H4 (Marleni), H5 (Milton, provisional), H6 (Arte Ambiguo), H18 (Taibará). The user identified the provided H25 (Centro de Inspiración) GPS coordinate as **another nearby building** and approved using the image-predicted H25 instead. Both source H25 coordinate and the predicted one are preserved. H25 excluded from fitting.

## Method

A six-parameter affine transformation is fitted from archived image x/y to local east/north metres (spherical WGS84 approximation at latitude 6.245), then converted into approximate lat/lon. A scale-and-rotation-only fit is inadequate. Diagnostics include fitting residuals and independent leave-one-out predictions. Held-out errors can exceed 100 m: these outputs must not be used as surveyed line lengths, exact service taps, rooftop layouts or verified property limits. Names are omitted from new geocoded exports to avoid creating an unnecessary name-location index. Coordinates remain research estimates only.

Existing archived 8-house *proximity* groups are copied as IDs only; they are **not** transformer IDs. The original traced LV line was digitized on a **different screenshot**. Its pixels cannot be mapped using this photo's affine transform. H18/H25 might be facilities, but all 35 sites are retained because the exact 33-household roster is unknown.

## Files

- `landmark_controls.csv`: source values, including excluded H25.
- `georeference.py`: reproducible pure-standard-library coordinate estimator.
- `house_points_provisional.csv` / `.geojson`: all 35 estimated points by ID.
- `control_points_supplied.geojson`: supplied GPS anchors, separately labelled.
- `georeferencing_diagnostics.json`: transformation, residuals, held-out errors.
- `map.html`: OSM Leaflet research overlay (internet needed for OSM/Leaflet). Do not upload these estimated points into OpenStreetMap.
- `epm_fetch.py`: opt-in infrastructure-only EPM public ArcGIS query, no meter/customer-personal datasets.

## EPM schema provenance and strict boundary

Public REST service: https://podascens.epm.com.co/arcgis/rest/services/Disponibilidad2023/MapServer . Published layers are 0 (autogeneration transformer availability), 3 (LV nodes), 5 (transformers), 6 (LV sections), 7 (MV sections). **Schema availability does not prove that geographic feature queries work, nor does proximity prove utility connectivity.** Query only necessary public infrastructure fields, document pagination/errors, and never publish customer names or meter accounts. EPM 94022 remains archived evidence, not a new verified live EPM record. EPM 92395 coordinates and reserve transformer identity remain unknown. `epm_query_status.json` records the present provenance.

## Run

```bash
python case1/studies/community_georef/georeference.py
python -m unittest discover -s case1/studies/community_georef -p 'test_*.py' -v
python case1/studies/community_georef/epm_fetch.py --outdir /tmp/san_rafael_epm_probe
```

A separate merge request should incorporate *verified* EPM layer observations into an actual pandapower network after inspection of geometric coverage, valid asset IDs and LV node connectivity. This MR does not change PyPSA v18, pandapower v5, Case1 v3, original 35-point source, or 11,515 historic results. Parked critical/deferrable load assumptions remain out of scope.


## Observed live EPM REST coverage (26 October 2026)

GitLab CI [pipeline #2990746440](https://gitlab.com/KKhan02/resilient-energy-systems/-/pipelines/2990746440), [probe job #17476958299](https://gitlab.com/KKhan02/resilient-energy-systems/-/jobs/17476958299), queried the public `Disponibilidad2023` REST service. **These are actual query responses, not schema-only assumptions:**

- Bounded El Arenal WGS84 search: **0 features returned** from each of layers 0 transformer availability, 3 LV electrical nodes, 5 transformers, 6 LV sections, 7 MV sections.
- Unfiltered service count for layer 0: **25,760** records, and layer 5: **25,763** records.
- Exact string code-count queries for **94022** and **92395** returned **0** in both transformer layers.

Thus the published service is populated elsewhere but supplied **no usable local EPM geometry** in this query. This does **not** invalidate the separately archived 94022/92395 evidence, determine which houses are supplied, or prove these transformers do not exist in EPM's current network. Dataset age, code mapping, access scope and alternative official EPM viewer layer backing require further verification. Do not draw fictitious LV feeders or update pandapower topology based on an empty layer. The official current [EPM energy network viewer](https://experience.arcgis.com/experience/742f0b4891f346b68e5512f807b80387?locale=es) is a separate entry point and has not had its underlying feature-service query established here.

The bounded query footprints/status are reproduced by `epm_fetch.py`; dated results are committed in `epm_query_status.json`. Zero-feature returned snapshots exist as an auditable CI artifact, not asserted real-world absence.
