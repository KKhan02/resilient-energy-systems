# San Rafael spatial and electrical evidence reconciliation

Status: SOURCE AUDIT ONLY. No new transformer, feeder, PV/BESS design or pandapower study has been implemented.

## Findings

The original spatial work is already present in this GitLab project under Energy Community - San Rafael/SanRafael_Reproducible_Model_Package_v2/.

**Transformer 94022:** The archived EPM asset CSV identifies node 931076, circuit 221-12, rating 5 kVA, primary 7.621 kV, secondary 240/120 V, latitude 6.246949759 and longitude -75.006208238. The transformer popup, conductor information and route context screenshots are also archived. This is supplied historical EPM evidence, not an independent current utility re-verification.

**35 houses:** The archived satellite image shows 35 numbered properties. The house coordinates CSV contains all IDs 1 through 35 with x/y pixels, but *zero of those rows contains lat/lon*. Therefore these points are NOT yet georeferenced WGS84 household connection nodes. Nor does the archive prove that all 35 are served by transformer 94022.

**Traced routes:** Primary and secondary pixel-point CSVs, scale calibration and generated lengths are present. The reproducible secondary polyline is 324.452085 m with a 30 m / 126 pixel scale, used as approximately 324.5 m by pandapower. The original local-geometry register separately states 328.8 m LV. Difference ~4.348 m / 1.34%; the discrepancy is not yet resolved. MV is 354.154665 m from the trace (register says 354.2 m). None is a surveyed cable route.

**Clustering:** The original four-through-eight-house grouping datasets cover 35 houses and produce respectively 9, 7, 6, 5 and 5 proximity groups. The grouping generator creates one hypothetical *5 kVA transformer centroid* per group, and the edges include transformer_upstream_placeholder records. These are NOT existing EPM transformer assets or confirmed network connections. They should be reused for household proximity and candidate shared PV/BESS locations only, not added as free electrical capacity.

**Notebook revisions are already tracked:** The original `Energy Community - San Rafael/` folder has the historic PyPSA v17 (34 cells) and 37-cell pandapower notebook. The SAME development GitLab repository already contains **the newer v18 (38 cells) and pandapower v5 (44 cells)** at `case1/legacy/`. Their GitLab SHA-256 metadata MATCHES the uploaded local originals exactly: PyPSA `0ed79c7cd19de757fb3daf7177752c6a5df82c95079a19519a048c8c63ae6ebc`; pandapower `35a0dfbcbb2bd2d251c03f34a176bf9c3f5654a4cf9cab1970646dea10985652`. They DO NOT require re-upload. The GWDG university GitLab instance remains separately unverified.

**Existing network model:** The supplied v5 uses the 5 kVA 120/240 V single-phase transformer represented by a balanced equivalent, a ~324.5 m radial LV feeder and two houses per representative tap. It already distinguishes fixed-route headroom from optional added-tap route expansion. It does NOT prove real individual service-drop lengths, leg/neutral imbalance, actual transformer customer allocation or farthest real household voltage.

## Project-to-asset distances — separate from feeder length

Using the archived EPM asset point (6.246949759, -75.006208238), original study point (6.247457120, -75.007881146) and candidate Site A point (6.248376671, -75.009321569), approximate geodesic separations are 193.4 m (asset to study point), 378.9 m (asset to Site A) and 189.1 m (study point to Site A). These are STRAIGHT-LINE DISTANCES, not validated feeder routes or electrical cable lengths.

## Source-of-truth rule

Original archived asset extract and screenshots -> historic utility asset references;
Original digitized map and calibration CSVs -> image evidence and pixel-distance calculations;
Original grouping CSVs -> hypothetical spatial group memberships, NEVER confirmed transformer territories;
Older GitLab notebooks -> historic code revisions;
Exact uploaded PyPSA v18/pandapower v5 -> already versioned in `case1/legacy/` development GitLab;
Case1 v3 outputs -> historical stale aggregate result population pending reproducible rerun;
Site A solar -> explicitly hypothetical level-ground and tree obstruction study.

The exact file-to-file crosswalk is in SOURCE_CROSSWALK.csv. OPEN_DATA_GATES.csv lists the genuine remaining verification gates.

## Consequences for next modelling phase — NO NEW TRANSFORMERS BY DEFAULT

1. Use the existing transformer 94022 and the v5 representative network as baseline, with stated limitations.
2. Georeference the 35 image points, then seek evidence of which houses are connected to 94022. If impossible, compare clearly hypothetical existing-feeder assignments instead of inventing a true one.
3. Resolve/document 324.452 versus 328.8 m before reporting an exact measured LV route.
4. For PV/BESS expansion, use household proximity clusters as proposed shared-generation sites, not as new EPM transformer substations. All cluster injections remain subject to the same existing network/PCC unless a separately justified and costed connection alternative is studied.
5. pandapower must check worst-house voltage, feeder loading, losses, reverse flows and transformer loading under independently specified siting. Avoid claiming the current 5 kVA transformer can supply 20 households.
6. Use the verified current notebooks under `case1/legacy/`; preserve original historic notebooks. Check the university GWDG instance separately rather than assuming both mirrors have identical revisions.
7. Critical and deferrable load assumptions are parked completely pending discussion with the professor; do not use 30% / 15% categories.

This audit does not authorize PV sizing, new network assets or islanding assumptions, and does not certify field topology.

## Reserve visit and household-count clarification

Participant reports visiting a reserve at **6.251758291989109, -75.0141263961902**, near an **EPM-map-verifiable 5 kVA transformer**. This is the **reserve reference coordinate**, NOT the verified geographic position or asset ID of its transformer. The asset number, exact pole, circuit, and supplied households are unknown. The reserve coordinate is approximately **1,025.6 m straight-line** from archived transformer **94022** (6.246949759, -75.006208238), so they must NOT be conflated or automatically assigned to one LV network. The official EPM viewer should be used to record the new asset ID before modelling; no new simulated transformer has been added.

The user refers to **33 houses**, whereas the existing satellite image includes **35 numbered sites**. At least two labels—H18 **GLAMPING TAIBARA** and H25 **CENTRO INSP**—appear to describe facilities, making 33 residences a *possible* interpretation rather than a verified count. Do NOT exclude two sites automatically, classify facilities without a confirmed roster, or assume all 35/33 belong to 94022. Coordinate and electricity-customer assignment remain unresolved.
