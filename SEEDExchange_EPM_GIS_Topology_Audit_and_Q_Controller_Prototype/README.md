# EPM public GIS evidence audit: San Rafael / El Arenal

**Input:** user-supplied `epm_gis.zip`. The attached `epm_network_to_kml.py` identifies EPM ArcGIS FeatureServer `P_Redes_Energia_GE3`, layers 4 (transformers), 7 (poles), 12 (LV) and 13 (MV). The full archive contains two different bounding-box extracts, `epm_kml` and `epm_kml_5km`. The latter was used for the audit.

## Key findings

- Wider extract: **267 transformer features, 1,658 LV sections, 550 MV sections and 2,175 poles**.
- All six known 3/5 kVA transformers are in the wider transformer layer. The northern 25 kVA unit still lacks a confirmed matching EPM asset ID.
- Official `NODO_TRANSFORM_CONN` IDs link **30 LV sections** to five named transformers. For these five, the `NODO1_ID` and `NODO2_ID` edge graph forms **one connected acyclic network rooted at the transformer's `NODO2_ID`**, subject to the one terminal field marked `0` for 113699.
- Transformer **92395** is present but **zero LV sections match its node `923848`** within either export. This is an evidence gap, not proof of a disconnected transformer.
- Transformer-linked LV mapped lengths are **288 m (94022)**, **726 m (106039)**, **429.49 m (113699)**, **85 m (85398)** and **360 m (98380)**. These are recorded *LV segments*, not complete verified service-route lengths to all candidate homes.
- Of 35 provisional houses, the nearest mapped LV section has the same transformer node as the *provisional allocation* for **26 houses**. This is proximity evidence only. Some candidate households are far from the mapped LV: e.g. H01 is 326.6 m, H06 315.3 m and H14 465.7 m away from their assigned transformer's nearest mapped LV. H30-H33 have no LV section with node 923848 in the export. These gaps must not be silently bridged with a made-up cable.
- Status fields record these as EPM network asset features, but no field validation, meter service-drop layer, energized connectivity verification, per-house phase mapping or verified line electrical impedances are supplied.

## Why it changes the model

Previous validation linked transformer coordinates to houses with speculative MST/star feeders and distance multipliers (1.0, 1.3, 1.6). For five EPM transformers, **we can now instead use mapped LV conductor sections and the EPM node graph**. Detached household connection geometry and line impedance are still assumptions. The existing MST/star results remain useful counterfactual sensitivities, not the primary baseline when GIS evidence is available.

Do not compare 288 m of *mapped LV sections* to the previous 2 km of *hypothetical household connections* as if they are the same quantity.

## Files

- `gis_transformer_lv_crosswalk.csv`: asset IDs, found line sections and lengths.
- `epm_node_graph_validation.csv`: topology root connectivity and radiality.
- `gis_matched_lv_segments.csv`: source line IDs, endpoint-node IDs, EPM conductor material, size, recorded length and geographic length.
- `house_to_epm_line_proximity.csv`: Euclidean shortest distance from each house to its assigned and to any EPM LV segment. Not customer-connection verification.
- `epm_network_relevant_sanitized.geojson`: relevant-area EPM features with only technical attributes, omitting vendor usernames/contract/person fields.
- `epm_lv_lines_and_candidate_houses.png` and `.svg`: visual cross-check with line layer by associated transformer; missing 92395 LV lines remain absent.
- `audit_epm_gis.py` and `reconstruct_epm_nodes.py`: reproducible audit code. Run from directory adjoining original `epm_gis.zip` (or update its path).

## Reactive-power controller prototype

The `q_control_patch/` files add optional Q control to the **existing hypothetical** `geographic_pandapower_v1` driver, *not yet to a rebuilt EPM-line network*. They are included to establish the controller algorithms and allow side-by-side tests while the EPM-grounded feeder model is constructed. Six pure unit tests passed. This environment does not have pandapower, so controller AC simulations have **not been executed or verified** here.

Modes: unity Q=0; fixed-PF Q injection; fixed-PF Q absorption; Volt–Var using illustrative points 0.96, 0.99, 1.01, 1.04 pu. Available Q is capped by both the inverter apparent-power circle and an assumed ±0.48 of the rated inverter kVA. These points and limits must be labelled model assumptions, not EPM setpoints.

The 5 kVA transformer base scenarios' fixed-PV minimum annual-cost designs use **10 kVA inverter rating for 10 houses** and **12 kVA for 12 houses** in the uploaded optimization CSV. Do not confuse inverter rating with transformer rating. The `P` schedule remains fixed, so this is **reactive support only**, not coordinated AC reoptimization. Observe maximum transformer kVA loading when adding Q.

### Install optional Q patch

Extract `q_control_patch/case1/studies/geographic_pandapower_v1/*` into the same relative folder in your repository. It adds `voltvar_control.py` and `run_geo_validation_q_control.py`; it does not overwrite the original `run_geo_validation.py`.

From `case1/studies/geographic_pandapower_v1`, first run:

```bat
python -m unittest discover -s tests -v
python run_geo_validation_q_control.py --mode critical --trafos 94022 --design optimized --inverter-kva 10 --routing mst --distance-factors 1.3 --siting head middle end --allocation equal --power-factors 0.98 --q-controls unity fixed_pf_inject fixed_pf_absorb volt_var --output outputs/q_94022_prototype
python run_geo_validation_q_control.py --mode critical --trafos 106039 --design optimized --inverter-kva 12 --routing mst --distance-factors 1.3 --siting head middle end --allocation equal --power-factors 0.98 --q-controls unity fixed_pf_inject fixed_pf_absorb volt_var --output outputs/q_106039_prototype
```

**Do not put preliminary Q-control results from the hypothetical feeder on the poster as EPM-line results.** The next decisive step is to build pandapower directly from the EPM line endpoint-node graphs, attach household loads through *explicit* provisional service drops, map conductor codes to justified R/X and ampacity assumptions, then rerun the three inverter controls. Where a house lies hundreds of metres from the nearest EPM LV segment, run alternative house associations and a missing-service-geometry scenario rather than treating a very long drop as established fact.
