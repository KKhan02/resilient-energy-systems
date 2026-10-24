# Case 1 — Results

San Rafael / El Arenal, transformer 94022 (5 kVA, single-phase, circuit 221-12).

Base configuration: 4 households, NASA POWER GHI + Erbs 2025 PV resource,
causal controllers, permissible transformer loading 0.90 pu, import power
factor 0.95. Every number below is reproduced by `python run_case1.py` and
written to `results_case1/`.

Baseline validation: **98/98 checks pass** against PyPSA v18 and pandapower v5
before any Case 1 extension is applied.

---

## 1. Answer to the research question

**Centralized PV can be doubled behind the existing 5 kVA transformer — from
5.22 kWp to 10.44 kWp — but only with active export control, and the binding
constraint is transformer thermal loading, not voltage.**

`network_export_control_counterfactual.csv`, critical hours solved in pandapower:

| PV | Inverter | Export held to envelope | Export limited only by inverter |
|---|---|---|---|
| 5.22 kWp (12 panels) | SUN-5K | 56.9 % loading — feasible | 56.9 % — feasible |
| 6.96 kWp (16 panels) | SUN-5K | 82.0 % — feasible | 82.0 % — feasible |
| 8.70 kWp (20 panels) | SUN-6K | 89.0 % — feasible | **105.2 % — infeasible** |
| 10.44 kWp (24 panels) | SUN-7.6K | 89.1 % — feasible | **130.5 % — infeasible** |

* Below 7 kWp the quoted SUN-5K's own 5 kW AC rating already acts as an export
  limiter, so control changes nothing. Control only starts to matter once the
  inverter is large enough to push past the transformer.
* LV voltage stays within 0.976–1.022 pu in **every** case, controlled or not,
  against a 0.97–1.03 pu screen. Voltage is not the limit at this site; the
  transformer is.
* The price of control is small: 0.14 % curtailment at 8.70 kWp and 1.83 % at
  10.44 kWp, while operational self-sufficiency rises 82.9 % → 99.5 % → 99.9 %.

---

## 2. The transformer envelope (objective 3)

The 5 kVA nameplate is apparent power. The usable active-power envelope is
`5 kVA × k_loading × pf`:

| k_loading | pf 0.90 | pf 0.95 | pf 1.00 |
|---|---|---|---|
| 0.80 | 3.60 kW | 3.80 kW | 4.00 kW |
| 0.90 | 4.05 kW | **4.275 kW** | 4.50 kW |
| 1.00 | 4.50 kW | 4.75 kW | 5.00 kW |

Largest household group served with **no** unserved energy
(`transformer_sensitivity.csv`):

| k_loading | pf 0.90 | pf 0.95 | pf 1.00 |
|---|---|---|---|
| 0.80 | 6 houses | 7 | 7 |
| 0.90 | 7 houses | **8** | 8 |
| 1.00 | 8 houses | 8 | 8 |

The permissible-loading factor is an **assumed** parameter — no EPM continuous
rating document was obtained — and it decides whether 7 or 8 households can be
carried. Obtaining that rating is the single highest-value missing input in the
study.

v18's simplification (5 kVA read as 5 kW active) does **not** distort the
reference 12-panel case, because nothing binds there: peak import 2.17 kW and
peak export 2.86 kW both sit well inside the envelope. It does distort the
oversized cases.

---

## 3. PV, battery energy and battery power (objective 2)

### Battery energy drives self-sufficiency; battery power does not

`battery_energy_vs_power.csv`, 16 panels on a SUN-8K:

| Modules | Usable | Self-sufficiency at 2.5 kW DC | at 5.0 kW | at 7.5 kW |
|---|---|---|---|---|
| 2 | 8.65 kWh | 79.97 % | 79.97 % | 79.97 % |
| 4 | 17.30 kWh | 96.31 % | 96.63 % | 96.63 % |
| 6 | 25.95 kWh | 97.17 % | 97.63 % | 97.63 % |
| 8 | 34.60 kWh | 97.69 % | 98.16 % | 98.16 % |

Tripling battery power buys at most 0.47 pp; doubling energy from 2 to 4 modules
buys 16.7 pp. **Specify the BESS by energy. 2.5 kW DC is already adequate**, and
10 kW is not even feasible on a SUN-8K (9.12 kW battery port).

This question could not be asked in v18, which capped battery DC power at the
converter rating so energy and power moved together.

### Curtailment always needs two limits to bind at once

`curtailment_attribution.csv`. Every curtailed hour is `battery_full` combined
with a blocked AC path — never inverter-limited, never battery-power-limited:

| System | Export allowance | Binding limits | Hours | Curtailed |
|---|---|---|---|---|
| 24 panels / 8 modules | 4.5 kW (envelope) | battery_full + export_at_cap | 358 | 258 kWh (1.8 %) |
| 24 panels / 8 modules | 0 kW (blocked) | battery_full + export_blocked | 2,026 | 5,879 kWh (41.7 %) |
| 12 panels / 4 modules | 0 kW (blocked) | battery_full + export_blocked | 247 | 251 kWh (3.6 %) |

---

## 4. Control strategies (objective 6)

Reference system, 12 panels / 4 modules / SUN-5K. `control_comparison.csv` and
`vulnerability_by_family.csv`:

| Controller | Self-sufficiency | Outages with firm load served | …with all demand served | Min SOC |
|---|---|---|---|---|
| Conventional | 82.87 % | 38 % | 38 % | 0.10 |
| Export-limited (1.5 kW) | 82.87 % | 38 % | 38 % | 0.10 |
| Fixed reserve (50 %) | 78.04 % | **89 %** | **89 %** | 0.50 |
| Adaptive reserve | 82.08 % | 76 % | 76 % | 0.30 |
| Adaptive + load management | 82.08 % | **92 %** | 29 % | 0.30 |
| *LP, perfect foresight* | *82.87 %* | *not a control option* | — | — |

Reading this correctly matters:

* **Fixed reserve** is the genuinely robust strategy: it serves 89 % of sampled
  outages with nothing deferred, and it pays 4.8 pp of self-sufficiency for it.
* **Adaptive reserve** recovers almost all of that self-sufficiency (82.08 % vs
  82.87 %) and still serves 76 % of outages — a better trade than fixed reserve
  on energy, worse on resilience.
* **Adaptive + load management** looks best on firm load (92 %) but only because
  it postpones up to 2.13 kWh of deferrable demand; counting that backlog as a
  shortfall drops it to 29 %. It is shifting demand, not supplying it. Whether
  that counts depends on whether the deferred load can actually wait — a pump
  can, a light cannot. The package flags this automatically
  (`shifts_rather_than_supplies` in `vulnerability_index.csv`).
* **Export limiting costs nothing in resilience and nothing in self-sufficiency**
  — it only moves the transformer loading (57.4 % → 45.6 % at 1.5 kW). It is a
  network measure, not an energy measure.

### The LP is a bound, not a controller

The causal conventional rule reproduces the LP **exactly** on annual energy
(82.875 %, 1,300.159 kWh import, 3,508.721 kWh throughput). But the LP's export
peak is 2.531 kW against the causal controller's 2.864 kW for the same annual
energy: the LP is indifferent to *when* it exports, so its export peak is a
degenerate artefact. v18 handed that lower figure to the grid study. **Never use
an LP export peak for network planning** — it understates reverse flow by 13 %
here.

---

## 5. Economically useful size (objective 4)

The answer depends entirely on whether exported energy is compensated, which is
a regulatory question, so both regimes are reported (`pv_marginal_value.csv`,
`bess_marginal_value.csv`).

### Self-consumption only (no export credit) — conservative

| Step | Benefit per USD of annualized cost | Useful? |
|---|---|---|
| 12 → 16 panels | 3.01 | yes |
| 16 → 20 panels | 0.36 | **no** |
| 0 → 2 modules | 3.18 | yes |
| 2 → 4 modules | 1.62 | yes |
| 4 → 6 modules | 0.09 | **no** |

**Economic optimum: 16 panels (6.96 kWp) + 4 battery modules (17.3 kWh)**, giving
96.6 % self-sufficiency with **zero curtailment**, on the quoted SUN-5K.
LCOE 0.176 USD/kWh, NPC 17,091 USD.

### HOMER net metering (sellback 0.275 USD/kWh = 95 % of purchase)

Every increment pays: 24 panels still returns 2.52 USD per USD. There is **no
economic stop** within the tested range, so the only limit on oversizing is the
electrical one in §1. The battery meanwhile has essentially zero economic value
(0.006 USD per USD) because the export credit it displaces is worth nearly as
much as the import it avoids — an arithmetic consequence of the tariff, not a
judgement on storage. The battery in this project is bought for self-sufficiency
and resilience, which §4 scores separately.

---

## 6. Vulnerability (objectives 5, 7, 8)

100 scenarios per controller across five families, each starting from the state
of charge the system actually had at that moment in the annual run.

| Family | Scenarios | Source |
|---|---|---|
| Low solar | 9 | worst measured 3/5/7-day windows of the 2025 NASA year, plus 0.70 and 0.50 derates |
| Grid outage | 80 | 4/8/12/24/48 h on a month × hour-of-day grid |
| High demand | 3 | highest measured 3-day demand window, ×1.00 / ×1.25 / ×1.50 |
| High PV, export limited | 3 | highest measured irradiance window at 0 / 1.5 / 3.0 kW export |
| Combined | 5 | low solar + high demand; outage *after* a low-solar window; outage during peak demand; high PV with export blocked |

Reference system, firm load served:

| Family | Conventional | Fixed reserve | Adaptive | Adaptive + LM |
|---|---|---|---|---|
| Low solar | 100 % | 100 % | 100 % | 100 % |
| High demand | 100 % | 100 % | 100 % | 100 % |
| High PV, export limited | 100 % | 100 % | 100 % | 100 % |
| Grid outage | 38 % | 89 % | 76 % | 92 % |
| **Combined** | **40 %** | **60 %** | **60 %** | **80 %** |

Single stressors are survivable at this hardware size; **combined stressors are
what separate the strategies**. The worst case is an outage arriving at the end
of a low-solar window, which is exactly when a conventional self-consumption
controller has already discharged the battery to 10 %.

### Outage results are conditional

Every outage metric carries `islanding_confirmed = False` and
`hardware_confirmed_installed = False`. The Deye datasheet describes off-grid
operation and integrated anti-islanding, but no installation, backup-panel
wiring or interconnection agreement has been verified at El Arenal. These
results state the energy available for islanded operation **if** islanding is
commissioned — not demonstrated backup performance.

---

## 7. Reactive power is counterproductive here

`inverter_pf_sensitivity.csv`, worst export hour. Absorbing reactive power does
reduce voltage rise, but it consumes transformer capacity:

| System | PF 1.00 | PF 0.98 | PF 0.95 |
|---|---|---|---|
| 12 panels: loading / max V | 56.9 % / 1.009 pu | 60.1 % / 1.005 | 63.8 % / 1.003 |
| 24 panels: loading / max V | 88.8 % / 1.014 pu | 93.1 % / 1.009 | **98.3 %** / 1.006 |

Since voltage never approaches the 1.03 pu screen, reactive absorption buys
headroom that is not needed and spends headroom that is. **Keep the inverter at
unity power factor** unless a measured voltage problem appears. The Deye unit
supports 0.8 leading to 0.8 lagging, so the capability exists if it is ever
needed.

---

## 8. Uncertainty

30 redrawn demand realizations, causal adaptive + load-management controller
(`demand_uncertainty.csv`):

| System | Metric | P5 | P50 | P95 |
|---|---|---|---|---|
| 12P / 4B | Self-sufficiency | 81.85 % | 82.19 % | 82.53 % |
| 12P / 4B | Peak export | 2.47 kW | 2.66 kW | 2.91 kW |
| 12P / 4B | Transformer loading | 49.5 % | 53.4 % | 58.4 % |
| 24P / 8B | Self-sufficiency | 99.93 % | 99.99 % | 100.00 % |
| 24P / 8B | Transformer loading | 90.35 % | 90.40 % | 90.46 % |

The oversized system's transformer loading is almost deterministic because the
export cap binds: control, not weather or demand, sets the peak. That is the
same conclusion as §1, arrived at from the uncertainty side.

---

## 9. What to do next

1. **Get the EPM continuous rating for transformer 94022.** It decides 7 vs 8
   households and it is currently assumed.
2. **Validate household demand.** The model uses 1,898 kWh/household/year;
   four EPM invoices for a nearby service on the same circuit bill about
   1,055 kWh/year. If real demand is near the lower figure, every
   self-sufficiency number here is conservative and the useful PV size shrinks.
3. **Confirm whether exports are compensated** at a 5 kVA residential
   connection. It is the difference between "16 panels" and "as much as the
   transformer allows".
4. **Confirm islanding** before presenting any outage result as backup
   performance.
5. **Specify the export limit as a commissioning parameter**, not a hope. Every
   feasible oversized configuration in §1 depends on it.
