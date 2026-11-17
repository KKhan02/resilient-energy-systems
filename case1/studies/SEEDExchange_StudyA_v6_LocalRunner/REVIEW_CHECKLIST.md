# Study A v6.2 review checklist

- [x] User approved minimum-cost references, a higher self-sufficiency comparator and separately developed four-house candidate references.
- [x] Historical first 20 HOMER profiles match; Excel remains primary new-demand source.
- [x] 35 unique source-to-house mappings and exact 2025 energy totals checked in **synthetic unit tests only**.
- [x] A0/A1 populations are protected by expected invariants. **v6.2 determines A1 membership from house-to-transformer distance across the original six EPM transformers**, without using LV geometry for assignment. The three historical changes are regression expectations only. LV selection is solely an AC geometry proxy after transformer selection. H30-H33 remain with 92395 even though its LV GIS is absent.
- [x] Individual P(h,t) and Q(h,t) map to the matching GIS load buses in synthetic unit test; the original legacy equal-allocation driver was NOT modified.
- [x] Archived original source solver and Q controller reused by import, not reimplemented.
- [x] Causal PV-first energy and SOC physics tested on four synthetic hours, separate from annual perfect-foresight baseline.
- [x] No output overwrite, no GitLab writes, no historical campaign rerun.
- [ ] Full GitLab GIS integration test runs in the user's actual local checkout. Here, 13 synthetic tests passed and one integration test was skipped because the full checkout is not mounted.
- [ ] Actual v4 CSV column schemas and GitLab checkout compatibility checked on user's local machine.
- [ ] Actual 35-house input manifest passes locally.
- [ ] First paired A0/A1 24-hour gross pandapower tests pass, independently reviewed.
- [ ] First 8,760-hour fixed-hardware manufacturer-SOC PyPSA run completes locally.
- [ ] Original and causal control battery/SOC/curtailment reports cross-checked.
- [ ] First 8,760-hour paired AC replay and physical uncertainties reviewed.
- [ ] Further equipment selection/AC-constrained redispatch for 4-house cases and marginal AC cases.
