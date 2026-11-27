# Study B | WP3-to-WP5 integration and entry gates
**27 November 2026 | Proposed interface, not final physical design.**

Study A's selected quantitative assessment and figure publication are complete. Study B is the next principal study under [approved scope](../../RESEARCH_SCOPE_APPROVED_2026-11-07.md). Retain the research division in the team v2 release: Shehan/WP3 develops spatial grouping, siting and route evidence; WP5 integrates electrical and economic models. Do not prescribe WP3's clustering algorithm or repeat its independent research. The following interface describes how to normalize whichever credible method and GIS format WP3 supplies.

## B0: Frozen input gate

[Source audit](B0_SOURCE_AUDIT_2026-11-27.json) checks 306,600 demand values against the original frozen Excel-derived profiles, 8,760 aligned local-hour demand/PV timestamps, 35 fixed coordinate/profile identities and four release-manifest hashes. All pass. The release on main at 80abc7719cfe95b8fa9f9c001e04d5b7e73fb35e is a read-only input source; active modelling remains on sync. 35-house demand is 66,430 kWh/a (1,898 per house), H08 uses house_25_kw. Study A has 34 active homes, 64,532 kWh/a. Any direct A/B comparison must use identical 34-house membership or a separately labelled full-35 expansion comparison, and distinguish per-house indicators from matched totals.

## B1: Group and supply-position hypotheses

Study B uses all 35 properties as the candidate population, N=5..15. Compare multiple plausible geographically compact groups where meaningful, not a forced single nested sequence. Separate overlapping candidate-group experiments from a full disjoint 35-house partition. Only the latter may be summed to a 35-house system result. WP3 chooses and justifies its grouping/siting approach; possible methods for consideration are nearest-neighbour candidate sets, geographically constrained hierarchical grouping and capacitated partitions. Centroid, medoid and practically available supply positions can be compared, not assumed buildable. Distance-only ranking is insufficient for final site selection. Retain H08 in the inventory and make its participation explicit. Northern transformer 137468/NORTH_25KVA excluded. Site A tie is Study C, not a default Study B supply point.

## B2: Proposed normalization contract for WP3 output

Accept CSV/GeoJSON/GeoPackage or equivalent source, preserving original evidence. WP5 can normalize to these tables; the columns below are an interface, not an instruction that WP3 must use a particular GIS algorithm.

| Table | Required logical fields |
|---|---|
| Group roster | group ID, house ID, scenario/partition ID where applicable, membership method/evidence |
| Supply sites | site ID, latitude, longitude, proposed supply basis, access/land/terrain evidence, feasibility status |
| Network cases | case ID, group ID, site ID, topology STAR/MST, route basis, supply node ID, explicit rating hypothesis |
| Network nodes | case ID, node ID, node type (supply/house/junction), coordinates, house ID where applicable |
| Branches | case ID, branch ID, endpoint IDs, base length m, length method and source, conductor assumption or unknown |
| Site and route evidence | ID, evidence reference/date, limitation, physical or hypothetical status |

Gate checks: all house IDs resolve to frozen inputs; each group contains 5–15 distinct households; all-35 partitions cover each exactly once; exactly one supply root per independent LV network; no direct tie between independent transformer secondaries; edges finite and positive with no duplicates, graph connected and acyclic; all household nodes connected; no excluded northern assets; same group and supply site in controlled STAR/MST pairs; explicit route and conductor provenance; distinguish geometric edge distance from surveyed route. A geometric MST over household/root nodes is a baseline; any route-constrained branched alternative must be named as such, not automatically a minimum tree. Derive downstream household sets and peak coincidence from frozen 2025 profiles. Intermediate poles/junctions may be explicit when evidence exists. No silent deletion of unmatched or nonconvergent cases.

## B3: Electrical model preparation

Reuse `geographic_pandapower_v1/topology.py` distance and tree primitives only where applicable, not its old northern-assignment path or aggregate/scaled demand. Reuse Study A per-house time-series mapping and existing fixed-hardware/AC-aware tools. Begin with load-only and controlled fixed hardware across STAR/MST for each matched group/site; compare cable length, longest electrical route, downstream coincident load, min/max voltage, thermal loading, losses, infeasible hours, and inverter siting. The 5 kVA transformer is an initial planning hypothesis, not a universal constraint or rating decision. Keep source PF .95/.98/1, route factors 1/1.3/1.6 applied to the declared base route only, .95–1.05 pu main limits, .97–1.03 optional sensitivity, 20% physical SOC, cyclic chronology, night Q off, zero-export/no-grid-charging historical baseline; confirm conductor and upstream supply basis before AC. Do not double-apply route detour factors to a route already scaled. Candidate supply is conditional; MV supply and protection must be evaluated before implementation.

## B4: Comparative sizing and robustness

Reuse original 6,840-task archive and 1,255 distinct designs as equipment candidate pool, not as evidence of new topology feasibility. Compare matched total hardware first to isolate spatial/connection effects; recompute dispatch for exact cohort traces and architecture. Then evaluate architecture-specific discrete sizing where new constraints change the investment decision. Apply common time samples, followed by full 8,760-hour reference/severe runs for decision-relevant alternatives; retain failures and only use bounded corrective redispatch when justified. Include reference AC loss sensitivity, energy cost, imports, SS, DC curtailment, battery throughput, voltage/thermal margins; keep unknown cable/civil/transformer/site/protection/metering costs distinct and develop evidence-backed cost scenarios with WP2/WP3. No fixed arbitrary case cap. No unapproved islanding, critical-load fractions, or physical interconnection.

## B5: Integration

WP1 resilience, WP2 economic/regulatory and WP4 inverter/protection evidence enter as reviewed extensions, not silent changes to frozen inputs. Compare B against A with matched households and C only when Site A alternatives are ready. Keep source, configuration, executable Python and results manifests versioned. Figures from actual Python-generated result tables only.

**Current state:** B0 passed; B1/B2 interface prepared, no specific groups, site, conductor, transformer upgrade, routes, or clustering algorithm selected. No new PyPSA/pandapower solves. Await or develop WP3 geometry evidence before numerical B3 launch. This is a preparatory specification for WP5, not a change to the approved research scope or the team work packages.
