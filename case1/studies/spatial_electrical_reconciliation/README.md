# San Rafael spatial and electrical evidence reconciliation

Status: SOURCE AUDIT ONLY. No new transformer, feeder, PV/BESS design or pandapower study has been implemented.

## Findings

The original spatial work is already present in this GitLab project under Energy Community - San Rafael/SanRafael_Reproducible_Model_Package_v2/.

**Transformer 94022:** The archived EPM asset CSV identifies node 931076, circuit 221-12, rating 5 kVA, primary 7.621 kV, secondary 240/120 V, latitude 6.246949759 and longitude -75.006208238. The transformer popup, conductor information and route context screenshots are also archived. This is supplied historical EPM evidence, not an independent current utility re-verification.

**35 houses:** The archived satellite image shows 35 numbered properties. The house coordinates CSV contains all IDs 1 through 35 with x/y pixels, but *zero of those rows contains lat/lon*. Therefore these points are NOT yet georeferenced WGS84 household connection nodes. Nor does the archive prove that all 35 are served by transformer 94022.

**Traced routes:** Primary and secondary pixel-point CSVs, scale calibration and generated lengths are present. The reproducible secondary polyline is 324.452085 m with a 30 m / 126 pixel scale, used as approximately 324.5 m by pandapower. The original local-geometry register separately states 328.8 m LV. Difference ~4.348 m / 1.34%; the discrepancy is not yet resolved. MV is 354.154665 m from the trace (register says 354.2 m). None is a surveyed cable route.

**Clustering:** The original four-through-eight-house grouping datasets cover 35 houses and produce respectively 9, 7, 6, 5 and 5 proximity groups. The grouping generator creates one hypothetical *5 kVA transformer centroid* per group, and the edges include transformer_upstream_placeholder records. These are NOT existing EPM transformer assets or confirmed network connections. They should be reused for household proximity and candidate shared PV/BESS locations only, not added as free electrical capacity.

**Notebooks differ by version:** The original GitLab PyPSA notebook is explicitly titled v17 (34 cells), while the project attachment SanRafael_PyPSA_Scenarios_v18_uncertainty.ipynb has 38 cells. The original GitLab pandapower notebook has 37 cells, while uploaded SanRafael_pandapower_Grid_Check_v5_uncertainty.ipynb has 44 cells. The uploaded v18/v5 notebooks have been examined but are NOT committed under those exact new version names. The original GitLab notebooks must not be mislabelled v18/v5.

**Existing network model:** The supplied v5 uses the 5 kVA 120/240 V single-phase transformer represented by a balanced equivalent, a ~324.5 m radial LV feeder and two houses per representative tap. It already distinguishes fixed-route headroom from optional added-tap route expansion. It does NOT prove real individual service-drop lengths, leg/neutral imbalance, actual transformer customer allocation or farthest real household voltage.

## Project-to-asset distances — separate from feeder length

Using the archived EPM asset point (6.246949759, -75.006208238), original study point (6.247457120, -75.007881146) and candidate Site A point (6.248376671, -75.009321569), approximate geodesic separations are 193.4 m (asset to study point), 378.9 m (asset to Site A) and 189.1 m (study point to Site A). These are STRAIGHT-LINE DISTANCES, not validated feeder routes or electrical cable lengths.

## Source-of-truth rule

Original archived asset extract and screenshots -> historic utility asset references;
Original digitized map and calibration CSVs -> image evidence and pixel-distance calculations;
Original grouping CSVs -> hypothetical spatial group memberships, NEVER confirmed transformer territories;
Older GitLab notebooks -> historic code revisions;
Separately uploaded PyPSA v18/pandapower v5 -> newer study notebooks until separately versioned;
Case1 v3 outputs -> historical stale aggregate result population pending reproducible rerun;
Site A solar -> explicitly hypothetical level-ground and tree obstruction study.

The exact file-to-file crosswalk is in SOURCE_CROSSWALK.csv. OPEN_DATA_GATES.csv lists the genuine remaining verification gates.

## Consequences for next modelling phase — NO NEW TRANSFORMERS BY DEFAULT

1. Use the existing transformer 94022 and the v5 representative network as baseline, with stated limitations.
2. Georeference the 35 image points, then seek evidence of which houses are connected to 94022. If impossible, compare clearly hypothetical existing-feeder assignments instead of inventing a true one.
3. Resolve/document 324.452 versus 328.8 m before reporting an exact measured LV route.
4. For PV/BESS expansion, use household proximity clusters as proposed shared-generation sites, not as new EPM transformer substations. All cluster injections remain subject to the same existing network/PCC unless a separately justified and costed connection alternative is studied.
5. pandapower must check worst-house voltage, feeder loading, losses, reverse flows and transformer loading under independently specified siting. Avoid claiming the current 5 kVA transformer can supply 20 households.
6. Version the supplied v18/v5 notebooks under explicit paths before describing the present GitLab original notebooks as the latest reference.
7. Critical and deferrable load assumptions are parked completely pending discussion with the professor; do not use 30% / 15% categories.

This audit does not authorize PV sizing, new network assets or islanding assumptions, and does not certify field topology.
