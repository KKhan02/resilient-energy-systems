# Ghana REPI | CURRENT STATUS

Updated: 2026-11-21.
Stage 00: Project workspace and reproducible pre-screen tools. **No community micro-grid or solar-home-system feasibility established.**

GitLab: KKhan02/resilient-energy-systems, dedicated branch study/ghana-repi; folder Ghana_REPI/.
Project separation: Do not edit Colombia/SEEDExchange code, branches or evidence. Reuse methodology only with documented Ghana-specific assumptions.

## Grounded evidence
- Uploaded "17 Nov_First Checkin.pdf", pp. 1-7: 21 communities (9 Savannah inland, 12 Oti islands) and 520 *survey respondents*, Savannah 222, Oti 298.
- Page 6 gives counts of questionnaire respondents, NOT complete community household totals.
- Page 7 provides village/community reference coordinates, not points of buildings/homes.
- Page 4 gives access-category examples: Dinnee and Tuonbo no grid; Jellinkon and Seripe grid present but homes not connected; Kawie/Kablima grid and household connections; Azizakpe island with grid. These are dated source statements, not a 2026 field verification.
- Pages 8-10 show screenshots of an underlying Excel questionnaire not provided as machine-readable source.

## Code / files
- Reference catalog transcribed and checked: data/reference/community_catalog_checkin.csv, 21 rows, sum 520.
- scripts/geo_screen.py: straight-line spatial household-screening, nearest neighbors, medoid, star/MST lower-bound lengths.
- scripts/demand_screen.py: measured/surveyed or labelled appliance-use entries -> indicative daily/yearly energy, NOT hourly peak.
- tests/test_screeners.py: unit and count checks.
- Empty data templates, provenance and privacy controls. No actual house positions or sampled household loads included.
- Local tests run on bootstrap source, 5/5 passed, user-local tests still pending.

## Immediate next gates
1. Confirm priority village and actual current electrification state; do not assume 2024-like status in 2026.
2. Obtain permission-cleared geolocated dwelling/building footprint locations, community boundaries and total houses. Distinguish buildings, households and respondents.
3. Obtain survey schema and sanitized appliance/use data; record how sampled respondents represent total households.
4. User runs test, geo and demand scripts locally and pushes sanitized results or discusses them.
5. Analyze clustering, route constraints, demand, level of service and economics before recommending mini-grid vs individual systems.

No invented coordinates, network ratings, load peaks or cost results. No feasibility decision using community reference coordinates alone.
