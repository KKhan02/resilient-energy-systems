# SEEDExchange Case Study 1 — El Arenal, San Rafael (Antioquia, Colombia)

**Transformer-Constrained PV-BESS Oversizing, Vulnerability and Adaptive Resilience Assessment**

> To what extent can centralized PV and battery capacities be increased behind the
> existing 5 kVA EPM transformer 94022 through controlled import/export, battery
> charging and PV curtailment, while maintaining electrical feasibility, improving
> energy independence, and reducing vulnerability to disturbances?

This package **extends** two verified baselines; it does not replace them.

| Baseline | Role |
|---|---|
| `SanRafael_PyPSA_Scenarios_v18_uncertainty.ipynb` | annual energy balance and dispatch |
| `SanRafael_pandapower_Grid_Check_v5_uncertainty.ipynb` | LV network screening |

The HOMER reference, the stochastic household demand model and the NASA POWER
GHI + Erbs PV model are ported with their physics unchanged. `validation.py`
asserts that this package reproduces the published v18 and v5 numbers **before**
any Case 1 extension is applied. If those checks fail, nothing downstream is
trustworthy — the pipeline says so and exits non-zero.

---

## 1. Running it

```bash
pip install pypsa highspy pandapower pvlib pandas numpy matplotlib

python run_case1.py                      # full study (~2 min)
python run_case1.py --validate-only      # only the baseline checks (~3 min)
python run_case1.py --annual-power-flow  # add 8,760 h power flow (~5 min more)
python run_case1.py --loading-limit 0.8 --pf-import 0.90
python run_case1.py --houses 8
pytest -q tests/                         # 38 tests (~25 s)
```

### Required inputs

**These are not shipped with the package — place your own copies before running.**
They are discovered in the working directory, `./data`, `./results` or the
parent directory:

| File | Status |
|---|---|
| `SimulacionTampico1k.xml` | accepted HOMER model |
| `NASA_POWER_SanRafael_hourly_2025.csv` | raw NASA POWER hourly weather |
| `Nasa Data.csv` | NASA POWER monthly radiation (optional; HOMER's monthly values are used if absent) |

The run prints which HOMER file it read and the key values parsed from it, so a
wrong or stale file is visible immediately.

Results are written to `./results_case1/` as CSV, figures to
`./results_case1/figures/`.

### Package layout

| Module | Contents |
|---|---|
| `config.py` | **every assumption**, each tagged MEASURED / DERIVED / REFERENCE / ASSUMED / CONTROL |
| `homer.py` | HOMER XML reader, battery bank sizing |
| `demand.py` | stochastic household demand; critical and deferrable splits |
| `resource.py` | HOMER-calibrated and NASA GHI + Erbs PV profiles; low-solar episode detection |
| `lp_model.py` | transformer-constrained PyPSA model (perfect-foresight **bound**) |
| `rule_dispatch.py` | **causal, no-forecast controllers** — the Case 1 decision engine |
| `kpi.py` | one KPI function scoring both engines from a standard dispatch table |
| `stress.py` | vulnerability scenarios and resilience metrics |
| `economics.py` | installed cost, replacements, NPC, economically useful size |
| `grid_check.py` | pandapower single-phase equivalent and feasibility screen |
| `sweeps.py` | design-space studies |
| `pipeline.py` | orchestration; writes every table |
| `validation.py` | v18 / v5 baseline checks |
| `figures.py` | figures (plots tables that are already saved; never a source of numbers) |

---

## 2. What changed from v18 / v5, and why

### 2.1 The 5 kVA limit is apparent power

v18 constrained active power at the point of common coupling to 5.0 kW, i.e. it
read the 5 kVA nameplate as 5 kW. Case 1 applies the apparent-power rating:

```
|S_pcc| = sqrt(P² + Q²) ≤ S_rated × k_loading
```

PyPSA solves active power only, so this enters the energy model as a derated,
**asymmetric** active-power envelope:

```
P_import_max = 5 kVA × k_loading × pf_import     = 4.275 kW   (k=0.90, pf=0.95)
P_export_max = 5 kVA × k_loading × pf_export     = 4.500 kW   (k=0.90, pf=1.00)
```

The apparent power implied by the solved flows is reported alongside, and the
authoritative value is recomputed in pandapower, which carries household
reactive power, inverter reactive power and network losses.

`k_loading` and `pf_import` are swept (0.80/0.90/1.00 × 0.90/0.95/1.00) because
no EPM continuous-rating document was obtained. **The 120 % factor in EPM
RA4-100 is for metering and CT selection and is not used here as a continuous
transformer loading limit.**

### 2.2 The inverter limit acts on the AC side

v18 set the PyPSA inverter link `p_nom` to the converter rating, which limits
the **DC input**, making the effective AC ceiling 0.95 × nameplate = 4.75 kW.
Case 1 limits the AC output to the datasheet rating.
`SystemSpec(inverter_limit_side="dc")` reproduces v18 exactly.

### 2.3 Battery energy and battery power are sized separately

v18 capped battery DC power at the converter rating, so energy and power moved
together and could not be studied independently (objective 2). Case 1 takes
energy from the module count and power from the lesser of the module count's DC
power and the inverter's **datasheet battery-port** current, with an explicit
override available.

### 2.4 Curtailment is accounted for explicitly

v18 reported dispatched PV only. Case 1 reports available, used and curtailed
PV, and attributes every curtailed hour to its binding limit: inverter AC,
export cap, export blocked, battery full or at power limit.

### 2.5 A causal controller, because the LP has perfect foresight

The PyPSA model solves the whole year in one linear program. Its dispatch
therefore **knows the future**. That is a legitimate upper bound, but it is not
a realistic reactive controller, and Case 1 forbids forecasting (that is
Case 2's rolling-horizon MPC). All Case 1 decision results come from
`rule_dispatch`, where at hour *t* a controller sees only the current PV, the
current demand, the current state of charge and trailing history. A test
asserts causality by perturbing the last hour of the year and checking that no
earlier hour changes.

Two consequences worth knowing:

* On the reference system the causal conventional rule **matches the LP exactly**
  on annual energy (82.875 % self-sufficiency, 1,300.159 kWh import,
  3,508.721 kWh throughput). Greedy local-first dispatch is optimal for
  self-consumption when nothing binds.
* The LP is **degenerate in export timing**, so its export peak is an artefact:
  2.531 kW against the causal controller's physically realistic 2.864 kW for the
  same annual energy. v18 handed the lower figure to the grid study. Never use
  an LP export peak as a network planning value.

---

## 3. Controllers (objective 6)

All five are causal. None uses a forecast.

| Controller | Rule |
|---|---|
| `CONVENTIONAL` | PV → load → battery → export; grid last; no reserve |
| `EXPORT_LIMITED` | as above with a lower PCC export cap |
| `FIXED_RESERVE` | will not discharge below a fixed emergency state of charge while the grid is available |
| `ADAPTIVE_RESERVE` | reserve rises when **trailing** solar availability falls (expanding mean of past days only) |
| `ADAPTIVE_PLUS_LM` | adaptive reserve plus same-day deferrable load management |
| `LP_PERFECT_FORESIGHT` | **not a control option** — an upper bound, always flagged `perfect_foresight=True` |

### Reading the load-management results honestly

Load management **shifts** demand; it does not supply it. Two survival measures
are always reported together:

* **firm load served** — no non-deferrable demand went unserved (credits deferral);
* **all demand served in window** — nothing unserved *and* nothing still deferred.

A controller that ranks well on the first and badly on the second is shifting
rather than supplying, and `vulnerability_index` flags exactly that with
`shifts_rather_than_supplies`.

---

## 4. Assumptions and provenance

`results_case1/parameter_provenance.csv` is generated from the registry in
`config.py` and tags every parameter:

| Tag | Meaning |
|---|---|
| `MEASURED` | EPM asset data, a datasheet, a bill or a downloaded dataset |
| `DERIVED` | computed from measured values inside this package |
| `REFERENCE` | from the accepted HOMER model or the project quotation |
| `ASSUMED` | engineering assumption; no site-specific value available |
| `CONTROL` | a study choice (scenario definition, sweep range, screening band) |

The assumptions that most affect the conclusions:

| Parameter | Value | Status |
|---|---|---|
| Transformer rating | 5 kVA single-phase, 7.621 kV / 240-120 V | MEASURED (EPM asset data) |
| Permissible loading | 0.90 pu, swept 0.80–1.00 | **ASSUMED** — no EPM continuous-rating document |
| Load power factor | 0.95, swept 0.90–1.00 | **ASSUMED** — EPM RA8-017 uses 0.90 for conductor sizing |
| Transformer `vk` / `vkr` | 3.0 % / 1.8 % | **ASSUMED** — 94022 nameplate not available |
| 1/0 AAC ampacity | 150 A | **ASSUMED** — installation-specific value not available |
| MV and LV reactance | 0.40 and 0.08 Ω/km | **ASSUMED** — installation geometry not available |
| Critical load share | 30 % of hourly demand | **ASSUMED** — no appliance survey |
| Deferrable load share | 15 % of daily energy, same-day | **ASSUMED** — no appliance survey |
| Household demand | 1,898 kWh/household/year | **REFERENCE**, synthetic — see §6 |
| Export compensation | 0.275 USD/kWh and 0.00 USD/kWh | both reported — a **regulatory** question |

### Hardware

The inverter datasheet supplied with the project is the Deye
**SUN-5K-SG02LP2-US-AM2**, a **split-phase 120/240 V** hybrid (grid connection
form 2L+N+PE) — the topology that matches the EPM 240/120 V single-phase
three-wire secondary, not a three-phase 400 V unit. Its datasheet limits are
enforced, and larger arrays step up through the same family:

| Model | AC [kW] | Max PV DC [kW] | Max panels (435 Wp) | Battery current [A] |
|---|---|---|---|---|
| SUN-5K | 5.0 | 7.5 | 17 | 120 |
| SUN-6K | 6.0 | 9.0 | 20 | 135 |
| SUN-7.6K | 7.6 | 11.4 | 26 | 190 |
| SUN-8K | 8.0 | 12.0 | 27 | 190 |
| SUN-10K | 10.0 | 15.0 | 34 | 220 |
| SUN-12K | 12.0 | 18.0 | 41 | 250 |

Configurations that breach a datasheet limit are **retained and flagged**
`hardware_feasible=False`, never silently corrected.

---

## 5. Validation

`python run_case1.py --validate-only` runs 98 checks against values transcribed
from the executed output cells of the baseline notebooks.

| Group | What is checked |
|---|---|
| `homer` | parsed component sizes, tariffs, efficiencies, variability settings |
| `demand` | annual energy, stochastic and deterministic peaks, clipped hours, 4–8 household peaks |
| `resource` | annual GHI and POA, POA/GHI ratio, Erbs closure, annual and peak PV DC, the v5 AC chain |
| `lp_s2_*` | the S2 reference case on both PV profiles, plus node balance and storage limits |
| `lp_house_sweep`, `lp_bess_sweep`, `lp_pv_sweep` | every v18 design sweep |
| `network_v5` | equivalent-circuit construction, the single-phase validation, annual voltage and loading extremes, the 9-house first overload |

The causal simulator additionally passes 15 physical consistency checks per run
(AC node balance, PV DC split, inverter conversion, state-of-charge balance,
power and energy limits, no simultaneous charge and discharge, no import or
export during an outage, demand accounting).

---

## 6. Limitations

These bound what the results can be used for.

1. **Household demand is synthetic.** It uses the HOMER variability settings
   (20 % day-to-day, 25 % timestep) applied to the HOMER monthly profiles, and
   the original HOMER random seed is not available. It has **not** been
   validated against measured consumption at El Arenal. Four EPM invoices for a
   nearby service on the same circuit (221-12, transformer 923494, San Carlos)
   bill roughly 1,055 kWh/year against the model's 1,898 kWh/household/year —
   a difference large enough that demand validation should precede any
   procurement decision. This is noted, not acted on: one service point on a
   different transformer, labelled "Provisional", is not a basis for re-anchoring
   the model.
2. **Hardware is proposed, not installed.** No commissioning, wiring or
   interconnection agreement has been verified.
3. **Islanding is unconfirmed.** The datasheet describes off-grid operation and
   integrated anti-islanding, but nothing at this site has been verified. Every
   outage metric carries `islanding_confirmed=False` and reports the energy
   available for islanded operation **if** islanding is commissioned — not
   demonstrated backup performance.
4. **The network model is a balanced equivalent**, not a split-phase model. It
   cannot represent 120 V leg imbalance.
5. **Routes are image-derived** (354.2 m MV, 324.5 m LV) and the LV feeder is
   representative, not surveyed house by house. High-house-count voltage results
   are sensitive to this geometry; the route-expansion sensitivity stays
   disabled until a measured added-tap spacing is supplied.
6. **Line loading percentages are screening values**, because the
   installation-specific 1/0 AAC ampacity and reactance are not known.
7. **Alternative hardware sizes are linear cost extrapolations**, anchored to the
   quotation subtotal. They are not supplier quotations.
8. **The 0.97–1.03 pu band is a 3 % design screen** from EPM RA8-017, not the
   complete Colombian statutory service-voltage limits.
9. **Monte Carlo quantifies seed-to-seed variation within the HOMER stochastic
   load formulation.** It does not make independent hourly Gaussian noise a
   measured household-load model.
10. **No forecasting anywhere.** Case 1 results are a floor on what a
    forecast-aware controller could achieve; Case 2's rolling-horizon MPC
    (24 h horizon, 3 h updates) is where that is tested.
