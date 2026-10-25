# San Rafael — Site A level-ground and tree-obstruction solar-access study

This is a **supporting, exploratory study**, not a selected PV installation design. The work is versioned in GitLab and executed by the independent GitLab CI solar job. No changes to the validated energy model, historic Case 1 results, or feeder/pandapower model are made.

## Physical inputs versus provisional assumptions

| Parameter | Value | Evidence classification |
|---|---|---|
| Project reference | 6.24745712023797, -75.00788114580126 | Project coordinates file |
| Site A candidate clearing | 6.248376671296207, -75.00932156861505 | User-proposed site point |
| Polygon | site_a_user_digitized_boundary.geojson | User-digitized satellite view; not surveyed |
| Gross polygon | ~1,759.26 m², 181.65 m perimeter | WGS84 geodesic calculation |
| Reference installation | 12 x 435 W PV; 4 x 5.12 kWh batteries; inverter/switchgear | Quoted starting point; 5.22 kWp / 20.48 kWh nominal |
| Complete-system 50 m² | Approximate reference package allowance | Project estimate, NOT measured site/ground mount layout |
| Usable land fraction | 25%, 50%, 75% | Hypothetical sensitivity; see site_area_scenarios.csv |
| Site surface | **Level ground** | Hypothetical engineering simplification, NOT measured |
| Array panel mid-height | 1.5 m | Hypothetical to define line-of-sight geometry |
| Surrounding tree height | 8, 12, 18 m | Hypothetical range; NOT measured |
| Tree setback to panel | 5, 10, 20 m | Hypothetical range; NOT measured |
| Tree azimuth bearings | all / east / west sectors | Hypothetical; no actual directions established |
| PV tilt and azimuth | horizontal; 10°, 20° north or south | Tested orientations only; no selection made |

The geometric obstruction elevation is atan(max(tree height minus panel mid-height, 0) / horizontal setback). Results for all nine pairs are in tree_height_setback_horizon_angles.csv. The whole-skyline assumption is a **stress bound**, not a prediction of all actual trees.

## Weather and shading approach

The existing Case 1 input file at **case1/data/NASA_POWER_SanRafael_hourly_2025.csv** contains 8,760 hourly local-solar-time values. It is a gridded NASA POWER point (6.2523, -75.0143), not Site A measurements. Annual 2025 GHI is **1,773.01 kWh/m²**; DHI **883.61 kWh/m²**; DNI **962.81 kWh/m²**. In 329 hours reported DHI exceeds GHI, so source components require later reconciliation; we do not silently correct the source.

The script uses **pvlib 0.16.1**, hourly midpoint solar position (fixed UTC-5), isotropic diffuse POA transposition, assumed ground albedo 0.2, and blocks **only direct-beam DNI** when the solar elevation is below an assumed elevation horizon. Sky diffuse loss, canopy width, near-field partial module shadows, string mismatch, temperature, soiling, converter behaviour and terrain are NOT modelled. The metric is **plane-of-array kWh/m²**, **not actual module DC or exported AC kWh**. No Site A tree shade percent is claimed as measured.

See the CSV provenance data, tests and numerical tables. Generated detailed pvlib tables, comparison figure and limitations JSON are retained in CI artifacts. This folder contains the **source and independent assumptions for reproduction**. The solar CI job must be green before using the generated numbers.

## How to reproduce

From the repository root after installing the already-pinned case1/requirements.txt, run:

    python case1/studies/site_a_solar/solar_access_pvlib.py --weather case1/data/NASA_POWER_SanRafael_hourly_2025.csv --outdir site_a_results

From the case1 directory, run regression tests:

    python -m pytest studies/site_a_solar/tests/test_solar_access.py -q

The new GitLab CI job case1_site_a_solar_screen performs both and archives outputs. No change to the main Case 1 run is made.

## Architectural comparison still open

Compare: **centralized PV+BESS at this clearing**, **distributed household PV+BESS**, and **distributed PV plus a common shared BESS**. No rooftop location, roof shading or realistic cable connection data are verified yet; therefore this Site A resource screen alone cannot rank architectures. The voltage-drop/weakest-house/feeder losses workstream belongs to **pandapower**, separately. Critical and deferrable demand shares are **fully parked**, as agreed.

**Next pre-design evidence** (not a requirement to run these sensitivities): independently verify land slope/ownership, usable area, actual tree canopy height and distance, array set-out, and access. A 3D near-shading/PVsyst study would be needed before treating simulated shadowing as installation-specific.

## Background

- NASA POWER hourly data: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/
- pvlib POA model: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_total_irradiance.html
- PVsyst near-shadings: https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/index.html
