# Ghana REPI | Community electrification study

Independent REPI case-study workspace. Repository: KKhan02/resilient-energy-systems. Branch: study/ghana-repi. Work exclusively inside Ghana_REPI/. The Colombia SEEDExchange research, its source files and main branch must remain untouched.

## Purpose and workflow
1. Establish which community is under study and verify its present electricity access.
2. Obtain total household numbers and real per-building coordinates or building footprints. Survey respondents are NOT total households.
3. Reconstruct demand from permission-cleared questionnaire responses and appliance inventory.
4. Screen geometry: straight-line household distances, indicative star and branched minimum-spanning-tree (MST) network lengths.
5. Compare mini-grid, smaller shared clusters, individual solar-home systems and grid extension, where applicable, using actual demand, feasible cable routes, voltages, service levels, cost, and affordability.
6. Develop hourly profiles, PV/BESS sizing, power flow and economic scenarios only when inputs justify them.

## Existing evidence
The user-provided PDF "17 Nov_First Checkin.pdf" pp. 1-7 describes 21 communities and 520 survey respondents: Oti 298, Savannah 222. Page 6 lists respondent counts. Page 7 lists COMMUNITY latitude/longitude, NOT household locations. Page 4 provides example electricity-access categories. Pages 8-10 contain questionnaire spreadsheet screenshots, not the underlying machine-readable survey. The PDF is not copied into GitLab.

data/reference/community_catalog_checkin.csv is a **transcription** of page-6 counts and page-7 coordinates. Its grid-access field records ONLY explicit page-4 examples and is not verified as current in 2026. Verify any spelling ambiguity and location precision before geospatial use.

## Local run (Python 3.10+, standard library only)
From the repository root after switching to the Ghana branch:

    python -m unittest discover -s Ghana_REPI/tests -v
    python Ghana_REPI/scripts/geo_screen.py --households Ghana_REPI/data/private/household_points.csv --community Chinekope --output Ghana_REPI/results/chinekope_geo
    python Ghana_REPI/scripts/demand_screen.py --appliances Ghana_REPI/data/private/appliance_demand.csv --community Chinekope --output Ghana_REPI/results/chinekope_demand

These analysis commands require user-provided ACTUAL anonymized household data. There are no example household coordinates or assumed loads. See data/README.md for schema. Geometry outputs give straight-line distances and a household medoid, not actual cable routes or permission to connect. Demand outputs give average energy, NOT peak power or hour-by-hour load.

## Git collaboration
Clone branch study/ghana-repi, work locally, run tests, inspect results, then selectively commit Ghana-only changes and sanitized output. Do not git-add sensitive respondent data or detailed private GPS-linked identities. raw inputs live at data/private/ (ignored) and generated results at results/ (ignored). Reviewed aggregate results may be explicitly added later.

CURRENT_STATUS.md is the authoritative handover. Append each validated run, input provenance, output location and uncertainties to ROLLING_UPDATES.md. Analysis decisions must be based on actual pushed evidence. Do not alter historical Colombia models or merge into main automatically.

## Missing data
Chosen community, 2026 grid status, full population/household count, house coordinates or building footprints, underlying questionnaire/data dictionary, actual appliances and usage, access routes, pricing, reliability targets and applicable regulatory parameters.
