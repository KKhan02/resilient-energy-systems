# San Rafael Energy Community PyPSA Model

## Detailed technical guide to the notebook, plots and result files

**Notebook documented:** `SanRafael_PyPSA_Scenarios.ipynb`  
**Model year:** 2025, 8,760 hourly snapshots  
**Primary modelling tool:** PyPSA with HiGHS  
**System boundary:** shared community PV + battery + 5 kVA EPM point of common coupling for a reference group of four households  
**Purpose:** quantify how much the community can reduce dependence on the EPM grid when locally generated PV and stored energy are used before grid imports.

This document explains what the PyPSA notebook does, how the modelling assumptions are implemented, how every major output should be interpreted, what each plot is intended to show, and how the generated CSV files are used in the wider San Rafael modelling workflow.

---

# 1. Role of PyPSA in the overall project

PyPSA is the **community energy-system and dispatch model**. It answers questions such as:

- How much of annual demand can be supplied locally?
- How much grid energy is still imported?
- How much PV is exported?
- How strongly is the battery cycled?
- How does self-sufficiency change with PV size, battery size, or number of households?
- What configurations meet specified self-sufficiency targets?
- How long can the reference system sustain a grid outage?
- Which hourly operating points should be passed to pandapower for detailed electrical-network analysis?

PyPSA is **not** the detailed distribution-network model. It does not calculate LV voltage drop, line current, conductor loading, phase imbalance, or transformer impedance effects. Those tasks are deliberately transferred to pandapower.

The modelling chain is therefore:

```text
HOMER / quotation / resource data
          |
          v
  common demand + PV profiles
          |
          v
        PyPSA
  energy balance / dispatch
          |
          +--> annual KPIs and design sweeps
          |
          +--> outage / resilience study
          |
          v
  hourly PCC, PV, load, battery traces
          |
          v
      pandapower
 detailed LV/MV network physics
```

The PyPSA model should therefore be interpreted as the **energy-management layer** of the project.

---

# 2. Main operating philosophy

The model is intentionally not tariff-driven.

The operating order is:

1. **PV supplies the community load directly.**
2. **Surplus PV charges the battery.**
3. **The battery discharges when PV is insufficient.**
4. **The grid supplies only the residual deficit.**
5. **Export occurs only after local demand and available storage have been satisfied.**

Grid charging of the battery is disabled in the normal community scenarios.

This is important because the project objective is **self-sufficiency and reduced grid dependence**, not short-term electricity-price arbitrage.

The grid generator is therefore assigned a large internal optimization coefficient of **10 USD/kWh**. This is an artificial priority coefficient and **must not be interpreted as an electricity tariff**. Actual grid costs are calculated after dispatch using the HOMER tariff values.

---

# 3. Reference system

The reference configuration used throughout the notebook is:

| Parameter | Reference value |
|---|---:|
| Households | 4 |
| PV modules | 12 |
| PV module rating | 435 W |
| PV array | 5.22 kWp DC |
| Inverter | 5 kW |
| Battery modules | 4 |
| Battery bank used in PyPSA | 19.2 kWh nominal, 17.3 kWh usable |
| Battery round-trip efficiency | 95% |
| Local transformer | 5 kVA |
| EPM primary voltage | 7.621 kV |
| LV voltage | 240/120 V |
| Annual four-house demand | 7,592 kWh |
| Reference quotation subtotal | 11,974.79 USD |
| Quotation total including VAT | 14,250.00 USD |

### Battery-capacity convention

The quotation identifies four Deye 5.12 kWh modules. The final HOMER model/report, however, represents the bank as **19.2 kWh nominal and 17.3 kWh usable**. The PyPSA reference follows the HOMER-modelled bank so that the energy-model comparison is internally consistent.

This should not be interpreted as changing the physical product name. It is a modelling-consistency choice.

---

# 4. Input data and provenance

## 4.1 HOMER XML

The notebook searches for:

- `SimulacionTampico1k(1).xml`
- `SimulacionTampico1k.xml`

either beside the notebook or under `data/`.

The XML supplies:

- PV size, CAPEX, replacement cost and lifetime
- inverter and rectifier sizes and efficiencies
- battery quantity, voltage, Ah rating, minimum SOC, round-trip efficiency, maximum charge current and lifetime throughput
- grid purchase and sellback tariffs
- project lifetime and real discount rate
- 12 monthly 24-hour demand profiles
- monthly solar radiation if NASA data are unavailable
- final HOMER annual PV production, load served, grid imports, grid exports, renewable fraction and battery throughput

The HOMER model is used as **reference data**, not as the dispatch rule that PyPSA tries to reproduce.

## 4.2 NASA POWER solar data

The notebook searches for:

- `Nasa Data(2).csv`
- `Nasa Data(1).csv`
- `Nasa Data.csv`

NASA POWER contributes the **monthly solar-resource pattern** through `ALLSKY_SFC_SW_DWN`.

The file is monthly/annual resource data, not an hourly irradiance time series.

PyPSA reconstructs an hourly PV shape from:

1. latitude-based daylight geometry,
2. monthly solar-radiation weighting,
3. deterministic daylight shape,
4. annual calibration to the final HOMER PV production.

For the 5.22 kWp reference array the calibrated annual DC production is exactly **7,326.3 kWh/year**.

## 4.3 Quotation

The installed-cost anchor is the actual quotation:

- subtotal: **11,974.79 USD**
- VAT: **2,275.21 USD**
- total: **14,250.00 USD**

Because the quotation does not itemize PV, battery and converter unit prices separately, alternative system sizes are **screening extrapolations**, not supplier quotations.

The HOMER component split is scaled to the quotation subtotal so the 12-panel / 4-battery reference returns exactly 11,974.79 USD before VAT.

## 4.4 EPM network reference

The PyPSA notebook stores metadata for the later pandapower model:

- transformer: **94022**
- EPM node: **931076**
- circuit: **221-12**
- transformer coordinates: **6.246949759, -75.006208238**
- MV voltage: **7.621 kV**
- LV voltage: **0.240 kV**
- transformer size: **5 kVA**
- primary conductor reference: **#2 ACSR**
- secondary conductor reference: **1/0 AAC**
- primary traced length: **354.2 m**
- secondary traced length: **324.5 m**
- two houses per LV branch

These values are metadata in PyPSA. Electrical line impedances and voltage-drop calculations belong to pandapower.

---

# 5. Notebook structure

The notebook is divided into 17 logical sections.

## Section 1: Global configuration

This section centralizes all scenario controls.

Important sweeps are:

```text
Households: 4, 5, 6, 7, 8
PV panels:  4, 6, 8, 10, 12
BESS:       0, 1, 2, 3, 4 modules
SS targets: 50, 60, 70, 80, 90, 95, 100 %
```

The practical PV limit is hard-capped at **12 panels**. No 14-panel configuration belongs to the current design space.

Execution switches allow individual studies to be enabled or disabled.

The normal configuration runs:

- core cases
- PV sweep
- battery sweep
- self-sufficiency design search
- reference outage
- outage-duration sweep

The shared-versus-individual study is disabled.

## Section 2: HOMER reference parser

`parse_homer_xml()` extracts all accepted reference-system parameters from the HOMER XML.

The section also builds the `HOMER` dictionary used throughout the notebook.

Battery wear is fixed to the final HOMER report value of **0.052 USD/kWh throughput**.

## Section 3: 8,760-hour demand profile

The final HOMER monthly 24-hour profiles are repeated through calendar year 2025.

The complete series is then normalized to:

- **7,592 kWh/year for four houses**
- **1,898 kWh/year per house**

For the 4–8-house study the same one-house profile is multiplied by the number of houses.

This means the house-count sweep changes total demand but **does not add household diversity**.

## Section 4: hourly PV availability

The notebook constructs a normalized hourly PV availability series.

The process is:

```text
monthly solar resource
        |
        v
solar geometry / daylight hours
        |
        v
deterministic hourly daylight shape
        |
        v
monthly weighting
        |
        v
annual scaling to 7,326.3 kWh
```

This guarantees agreement with HOMER on annual reference PV energy, while preserving a physically reasonable day/night pattern.

The exact hourly sequence is therefore synthetic and should not be interpreted as measured PV output.

## Section 5: LV branch metadata

The function `lv_branch_assignment()` creates radial branch metadata for pandapower.

With two houses per LV branch:

- 4 houses -> 2 branches
- 5–6 houses -> 3 branches
- 7–8 houses -> 4 branches

These are not separate PyPSA buses.

## Section 6: PyPSA network builder

The aggregated model contains three buses:

```text
GRID_MV
   |
TRAFO_PCC
   |
COMMUNITY_AC
   |
   +------ community load
   ^
   |
INVERTER
   |
 DC_BUS
   |
   +------ PV_DC
   |
   +------ BESS
```

### Grid

`GRID_IMPORT` is a generator on `GRID_MV`.

`GRID_EXPORT` is represented as a negative generator so residual energy can leave the community.

`TRAFO_PCC` limits active power exchange to the 5 kVA reference transformer rating.

### PV

PV is connected to the DC bus.

The generator nominal power is:

```text
number of panels x 0.435 kW
```

Its hourly maximum output is set by the calibrated availability profile.

### Inverter

The DC-to-AC inverter is modelled as a PyPSA link with **95% efficiency**.

### Battery

The BESS is a `StorageUnit` on the DC bus.

The four-module reference uses:

- 19.2 kWh nominal
- 17.3 kWh usable
- 95% round-trip efficiency
- charge/discharge efficiency split as `sqrt(0.95)`
- DC power limit restricted by battery current capability and inverter rating

Normal annual simulations use cyclic state of charge.

There is no AC-to-DC rectifier path in the normal local-first model, which prevents grid charging.

## Section 7: solution and KPIs

`calculate_kpis()` converts the hourly PyPSA solution into annual indicators.

The major definitions are described below.

---

# 6. KPI definitions

## 6.1 PV penetration

```text
PV penetration = annual PV DC generation / annual load
```

For the reference system:

- PV generation = 7,326.3 kWh
- load = 7,592 kWh
- PV penetration = **96.50%**

This does **not** mean 96.5% self-sufficiency.

## 6.2 Operational self-sufficiency

\[
SS = 100\left(1-\frac{E_{grid,import}}{E_{load}}\right)
\]

This is the main physical grid-dependence indicator.

A self-sufficiency value of 60% means gross annual grid imports are equivalent to 40% of annual demand.

For the PyPSA reference system:

- grid imports = **1109.8 kWh**
- self-sufficiency = **85.38%**

## 6.3 Net grid independence

The signed annual grid exchange is:

\[
E_{grid,net} = E_{import} - E_{export}
\]

Net grid independence is:

\[
NGI =
\min\left(
100,\,
100\left[
1-\frac{E_{grid,net}}{E_{load}}
\right]
\right)
\]

It credits exported energy against imported energy.

For the PyPSA reference:

- imports = **1109.8 kWh**
- exports = **308.7 kWh**
- net grid exchange = **801.1 kWh**
- net grid independence = **89.45%**

Self-sufficiency and net grid independence answer different questions and should both be retained.

## 6.4 Grid-independent hours

This is the percentage of hourly snapshots in which grid import is effectively zero.

It complements the annual energy metric by showing how often the community can operate without importing.

## 6.5 Battery throughput

For direct comparison with HOMER:

\[
E_{throughput}
=
\frac{E_{charge}+E_{discharge}}{2}
\]

This is intentionally not the simple sum of charge plus discharge.

The reference PyPSA result is:

- annual charge = **3560.4 kWh**
- annual discharge = **3382.4 kWh**
- throughput = **3471.4 kWh**

HOMER reports only **17.745 kWh/year** throughput, showing that its original dispatch barely uses the battery.

## 6.6 Screening cost

The design-search x-axis uses the deliberately simple metric requested for the workshop:

\[
C_{screening}
=
C_{CAPEX}
+
C_{grid,imports}^{annual}
\]

The grid-import term is:

\[
C_{grid,imports}^{annual}
=
E_{grid,import}
\times
c_{buy}
\]

Export credit is reported separately and is **not subtracted** from the screening cost.

This is a screening metric only. It combines an upfront capital amount with one year of grid-purchase cost, so it is not a lifecycle NPC, annualized cost, or LCOE.

The notebook also calculates annualized CAPEX and other economic fields, but the Pareto/design-screening plots use the explicitly requested **CAPEX + grid import cost** measure.

---

# 7. Core scenarios and current results

The current v16 result set is:

| Case                 |   Houses |   Panels |   BESS |   PV penetration [%] |   Self-sufficiency [%] |   Net grid independence [%] |   Grid import [kWh] |   Grid export [kWh] |   Battery throughput [kWh] |
|:---------------------|---------:|---------:|-------:|---------------------:|-----------------------:|----------------------------:|--------------------:|--------------------:|---------------------------:|
| S0_GRID_ONLY         |        4 |        0 |      0 |                 0    |                   0    |                        0    |             7592    |                0    |                       0    |
| S1_PV_ONLY           |        4 |       12 |      0 |                96.5  |                  43.06 |                       91.68 |             4323.12 |             3691.11 |                       0    |
| S2_REFERENCE_PV_BESS |        4 |       12 |      4 |                96.5  |                  85.38 |                       89.45 |             1109.85 |              308.71 |                    3471.41 |
| S3_FIXED_HW_4HH      |        4 |       12 |      4 |                96.5  |                  85.38 |                       89.45 |             1109.85 |              308.71 |                    3471.41 |
| S3_FIXED_HW_5HH      |        5 |       12 |      4 |                77.2  |                  71.74 |                       71.74 |             2681.42 |                0    |                    3107.84 |
| S3_FIXED_HW_6HH      |        6 |       12 |      4 |                64.33 |                  60.07 |                       60.07 |             4547.5  |                0    |                    2452.62 |
| S3_FIXED_HW_7HH      |        7 |       12 |      4 |                55.14 |                  51.71 |                       51.71 |             6416.04 |                0    |                    1847.84 |
| S3_FIXED_HW_8HH      |        8 |       12 |      4 |                48.25 |                  45.41 |                       45.41 |             8288.89 |                0    |                    1331.66 |

### Interpretation

`S0_GRID_ONLY` is the baseline.

`S1_PV_ONLY` demonstrates the timing problem clearly. Annual PV production is nearly equal to annual load, yet operational self-sufficiency is only about **43.1%** because daytime PV surplus is exported and later deficits are imported.

`S2_REFERENCE_PV_BESS` uses exactly the same annual PV energy but actively shifts energy through storage. Operational self-sufficiency rises to **85.38%**.

The 4–8-house sweep shows that the same hardware becomes progressively more grid-dependent as additional households are attached.

---

# 8. HOMER versus PyPSA comparison

The notebook deliberately distinguishes three different percentage metrics.

| Metric                           |   HOMER |   PyPSA |   Difference [pp] |
|:---------------------------------|--------:|--------:|------------------:|
| PV penetration [%]               |   96.5  |   96.5  |             -0    |
| Operational self-sufficiency [%] |   38.52 |   85.38 |             46.86 |
| Net grid independence [%]        |   91.62 |   89.45 |             -2.17 |

The annual energy-flow comparison is:

| Quantity                    |   HOMER |   PyPSA |
|:----------------------------|--------:|--------:|
| Load [kWh/yr]               | 7592    | 7592    |
| PV DC generation [kWh/yr]   | 7326.3  | 7326.3  |
| Grid imports [kWh/yr]       | 4667.4  | 1109.85 |
| Grid exports [kWh/yr]       | 4030.9  |  308.71 |
| Battery energy in [kWh/yr]  |   18.2  | 3560.42 |
| Battery energy out [kWh/yr] |   17.3  | 3382.4  |
| Battery throughput [kWh/yr] |   17.75 | 3471.41 |

### Why PyPSA self-sufficiency is much higher

HOMER and PyPSA use the same reference annual load and PV production.

The difference is dispatch.

HOMER:

- imports 4,667.4 kWh/year
- exports 4,030.9 kWh/year
- battery throughput 17.745 kWh/year

PyPSA local-first reference:

- imports **1109.8 kWh/year**
- exports **308.7 kWh/year**
- battery throughput **3471.4 kWh/year**

PyPSA therefore uses the battery as intended for local self-consumption, whereas the HOMER result mostly exchanges energy with the grid.

The trade-off is that HOMER's annual **net** import-export balance is slightly better, even though it is much more dependent on gross imports at the hours when demand occurs.

---

# 9. PV-size sweep

The PV sweep fixes:

- four houses
- four BESS modules
- 5 kW converter

and varies PV from 4 to **12 panels maximum**.

|   Panels |   PV [kWp] |   PV penetration [%] |   Self-sufficiency [%] |   Net grid independence [%] |   Import [kWh] |   Export [kWh] |   CAPEX + grid import cost [USD] |
|---------:|-----------:|---------------------:|-----------------------:|----------------------------:|---------------:|---------------:|---------------------------------:|
|        4 |       1.74 |                32.17 |                  30.52 |                       30.52 |        5275.26 |           0    |                          10929.9 |
|        6 |       2.61 |                48.25 |                  45.41 |                       45.41 |        4144.45 |           0    |                          11245.6 |
|        8 |       3.48 |                64.33 |                  60.07 |                       60.07 |        3031.67 |           0    |                          11566.6 |
|       10 |       4.35 |                80.42 |                  74.64 |                       74.67 |        1925.63 |           2.22 |                          11889.5 |
|       12 |       5.22 |                96.5  |                  85.38 |                       89.45 |        1109.85 |         308.71 |                          12296.6 |

The main trend is monotonic: larger PV arrays reduce gross grid imports and increase self-sufficiency.

At low PV size there is almost no export. Export only becomes material when generation begins to exceed simultaneous demand and available battery charging.

No configuration above 12 panels is allowed in the current model.

---

# 10. Battery-size sweep

The BESS sweep fixes:

- four houses
- 12 PV panels, 5.22 kWp
- 5 kW converter

and varies storage from 0 to 4 modules.

|   BESS modules |   Self-sufficiency [%] |   Import [kWh] |   Export [kWh] |   Battery throughput [kWh] |   CAPEX [USD] |   CAPEX + grid import cost [USD] |
|---------------:|-----------------------:|---------------:|---------------:|---------------------------:|--------------:|---------------------------------:|
|              0 |                  43.06 |        4323.12 |        3691.11 |                       0    |       7197.29 |                          8451    |
|              1 |                  62.31 |        2861.4  |        2152.45 |                    1579.14 |       8391.67 |                          9221.47 |
|              2 |                  81.04 |        1439.69 |         655.91 |                    3115.07 |       9586.04 |                         10003.5  |
|              3 |                  85.33 |        1113.85 |         312.93 |                    3467.08 |      10780.4  |                         11103.4  |
|              4 |                  85.38 |        1109.85 |         308.71 |                    3471.41 |      11974.8  |                         12296.6  |

The most important result is the sharp saturation between three and four battery modules.

Three BESS modules:

- self-sufficiency = **85.33%**
- grid imports = **1113.9 kWh/year**
- CAPEX = **10780 USD**

Four BESS modules:

- self-sufficiency = **85.38%**
- grid imports = **1109.8 kWh/year**
- CAPEX = **11975 USD**

The fourth battery therefore adds substantial CAPEX but almost no annual self-sufficiency improvement. Its remaining value is primarily additional resilience/storage margin rather than annual grid-import reduction.

---

# 11. Self-sufficiency design search

The full design search evaluates the practical combinations of:

- PV panels: 4, 6, 8, 10, 12
- BESS modules: 0, 1, 2, 3, 4

This gives **25 tested configurations**.

For each target, the notebook selects the feasible configuration with the lowest `CAPEX + annual gross grid-import cost`.

The unique selected steps in the current result set are:

| Configuration   |   Self-sufficiency [%] |   Net grid independence [%] |   Import [kWh] |   Grid import cost [USD/yr] |   CAPEX [USD] |   CAPEX + grid import cost [USD] |
|:----------------|-----------------------:|----------------------------:|---------------:|----------------------------:|--------------:|---------------------------------:|
| 8P / 1B         |                  57.2  |                       60.22 |        3249.04 |                      942.22 |       7104.31 |                          8046.54 |
| 10P / 1B        |                  61    |                       75.38 |        2960.51 |                      858.55 |       7747.99 |                          8606.54 |
| 10P / 2B        |                  72.74 |                       74.76 |        2069.42 |                      600.13 |       8942.37 |                          9542.5  |
| 12P / 2B        |                  81.04 |                       89.68 |        1439.69 |                      417.51 |       9586.04 |                         10003.5  |

Targets that are infeasible within the practical 12-panel design space are:

|   Target self-sufficiency [%] |   Feasible |
|------------------------------:|-----------:|
|                            90 |          0 |
|                            95 |          0 |
|                           100 |          0 |

The current model therefore reaches the 80% target but does not reach 90%, 95% or 100% with the allowed hardware combinations.

---

# 12. Pareto frontier

The Pareto figure uses:

- x-axis: **CAPEX + grid import cost [USD]**
- y-axis: **operational self-sufficiency [%]**

Every tested practical configuration is shown as a scatter point.

The Pareto line connects only non-dominated points.

A point is dominated if another tested configuration has:

- equal or lower screening cost, and
- equal or higher self-sufficiency,

with at least one strict improvement.

The Pareto plot is therefore not expected to connect all 25 configurations. It should, however, show all 25 candidate points in the background.

Only configurations with 12 panels or fewer are included.

---

# 13. Outage and resilience modelling

The outage study islands the community from EPM.

Assumptions:

- outage begins at `2025-09-15 18:00`
- initial battery SOC = 80%
- PV remains available
- grid import/export is unavailable
- load shedding is allowed and measured explicitly
- minimum battery SOC remains enforced

The duration sweep gives:

|   Outage [h] |   Start SOC [%] |   Demand [kWh] |   Energy not served [kWh] |   Load served [%] |   Minimum SOC [%] |   Ending SOC [%] |
|-------------:|----------------:|---------------:|--------------------------:|------------------:|------------------:|-----------------:|
|            4 |              80 |           5.65 |                      0    |            100    |             48.28 |            48.28 |
|            8 |              80 |           9.06 |                      0    |            100    |             29.11 |            29.11 |
|           12 |              80 |          12.02 |                      0    |            100    |             12.47 |            12.47 |
|           24 |              80 |          23.58 |                      0.18 |             99.25 |             10    |            10    |

The 4, 8 and 12-hour cases are fully served.

The 24-hour case serves **99.25%** of load, with only **0.177 kWh** unserved. The battery reaches its 10% minimum SOC.

This study is a resilience extension of the reference design, not a claim that the community is permanently island-capable.

---

# 14. Plot catalogue

All enabled figures are saved under:

```text
results/figures/
```

## `input_monthly_load_profiles.png`

Shows the 12 HOMER-derived representative 24-hour demand profiles.

**Use it to explain:** how the annual load series is constructed and how seasonal monthly demand shapes differ.

## `input_monthly_solar_resource.png`

Bar chart of monthly solar radiation.

**Use it to explain:** the seasonal resource weighting used in the synthetic hourly PV reconstruction.

## `pypsa_topology_4hh.png`

Schematic of the aggregated PyPSA topology.

**Use it to explain:** grid, PCC, AC bus, DC bus, PV, BESS, inverter and community load connectivity.

It is a topology diagram, not a geographic network drawing.

## `homer_reference_energy_context.png`

Shows HOMER annual load, PV production, grid purchases, grid sales and net grid import.

**Use it to explain:** why 96.5% PV penetration is not equivalent to self-sufficiency.

## `all_core_cases_self_sufficiency.png`

Compares operational self-sufficiency across the main core cases.

**Use it to explain:** the progression from grid only to PV only, PV+BESS, and increasing household group sizes.

## `house_sweep_energy_share.png`

Shows the locally supplied and grid-dependent shares as the same hardware serves more houses.

**Use it to explain:** how quickly fixed hardware loses autonomy as community demand increases.

## `pv_sweep_capex_plus_grid_cost_vs_self_sufficiency.png`

Plots PV-size configurations against:

- x: CAPEX + annual gross grid-import cost
- y: operational self-sufficiency

**Use it to explain:** the trade-off between larger PV arrays, higher investment and lower remaining grid dependence.

## `bess_sweep_capex_plus_grid_cost_vs_self_sufficiency.png`

Equivalent trade-off for the number of battery modules.

**Use it to explain:** diminishing returns from storage, especially the small improvement from the third to fourth battery.

## `self_sufficiency_pareto_frontier.png`

Plots all 25 practical PV/BESS combinations and highlights the non-dominated frontier.

**Use it to explain:** which tested designs offer the best combination of the chosen screening cost and operational self-sufficiency.

The plot is only valid for the explicitly defined screening metric. It is not a lifecycle-cost Pareto frontier.

## `self_sufficiency_vs_grid_import_cost.png`

Shows the remaining annual gross grid-import cost as self-sufficiency increases.

**Use it to explain:** the direct financial consequence of importing less electricity.

## `self_sufficiency_incremental_combined_cost.png`

Shows the change in `CAPEX + grid import cost` between successive selected self-sufficiency design steps.

**Use it to explain:** how much additional screening cost is associated with moving from one selected design level to the next.

## `homer_pypsa_metric_alignment.png`

Side-by-side comparison of:

- PV penetration
- operational self-sufficiency
- net grid independence

**Use it to explain:** that each metric must be compared with the same metric in the other model.

## `gross_vs_net_grid_independence.png`

Focuses specifically on:

- operational self-sufficiency based on gross imports
- net grid independence after crediting exports

**Use it to explain:** the difference between physical hourly dependence on EPM and annual net energy balance.

## `homer_pypsa_reference_energy_flows.png`

Compares HOMER and PyPSA reference:

- PV generation
- grid imports
- grid exports

**Use it to explain:** how the same annual PV energy leads to very different grid interaction because of different storage use.

## `homer_pypsa_battery_cycling.png`

Compares:

- battery energy in
- battery energy out
- annual throughput

between HOMER and PyPSA.

**Use it to explain:** the central reason for the self-sufficiency difference between the two models.

## `outage_dispatch.png`

Hourly outage power plot showing:

- demand
- AC supply from inverter
- battery power
- unserved load

Demand is deliberately drawn as a visible dashed line because it can overlap the AC-supply curve when all load is served.

**Use it to explain:** how PV and BESS cover load during islanded operation.

## `outage_battery_soc.png`

Battery SOC trajectory during the reference outage.

**Use it to explain:** energy margin, starting SOC and proximity to minimum allowed SOC.

## `outage_duration_load_served.png`

Load-served percentage for 4, 8, 12 and 24-hour outages.

**Use it to explain:** the resilience limit of the reference system.

## `shared_vs_individual_self_sufficiency.png`

A helper function exists, but this analysis is **disabled in v16**.

It should not be reported as a substantive result because every house currently uses the same normalized profile and the component model is linear. Distinct measured or stochastic household traces are required before this comparison becomes meaningful.

---

# 15. Generated CSV files

All normal numerical outputs are written under:

```text
results/
```

## `homer_reference_context.csv`

One-column HOMER reference table.

Contains:

- AC primary load
- PV production
- PV penetration
- grid purchases
- grid sales
- net grid import
- derived operational self-sufficiency
- derived net grid independence
- HOMER renewable fraction
- battery energy in
- battery energy out
- battery throughput

This is the cleanest file for citing the final HOMER benchmark quantities.

## `core_cases.csv`

One row per main PyPSA scenario.

Contains the full standard KPI set, including:

- hardware configuration
- demand and served load
- PV production and penetration
- inverter output and losses
- grid imports/exports
- self-sufficiency
- net grid independence
- grid-independent hours
- battery charge/discharge/throughput
- peak import/export
- CAPEX
- grid import cost
- export credit
- annualized economic indicators

Use this file for the main scenario comparison.

## `pv_panel_sweep.csv`

One row per PV-size case.

Current panel counts:

```text
4, 6, 8, 10, 12
```

Use it for:

- PV-size sensitivity
- PV trade-off plot
- checking the effect of increasing PV at fixed BESS

No 14-panel configuration should appear.

## `bess_module_sweep.csv`

One row for each BESS count from 0 to 4.

Use it for:

- storage sensitivity
- battery saturation analysis
- annual cycling comparison
- cost/self-sufficiency trade-off

## `self_sufficiency_candidates.csv`

The complete design-search dataset.

Current practical design grid:

```text
5 PV sizes x 5 BESS sizes = 25 configurations
```

This is the source for the Pareto scatter and frontier.

It should be used when a complete design-space view is needed rather than only the target-selected configurations.

## `self_sufficiency_design_steps.csv`

Contains only the unique configurations selected for self-sufficiency targets.

Additional columns include:

- requested target
- configuration label
- lowest/highest target represented by the same configuration
- CAPEX change from previous design
- self-sufficiency change
- grid-import cost saving
- combined screening-cost change

Use it for recommendation tables and incremental-design discussion.

## `self_sufficiency_infeasible_targets.csv`

Lists requested targets that cannot be reached within the practical design space.

Current infeasible targets:

```text
90%, 95%, 100%
```

## `outage_reference_case.csv`

Single-row summary of the configured reference outage.

Current reference:

```text
12 hours
80% starting SOC
```

## `outage_reference_dispatch.csv`

Hourly dispatch during the reference outage.

Contains the variables needed to reconstruct the outage plots and inspect exactly when the battery supplies the load or load shedding occurs.

## `outage_duration_sweep.csv`

One row each for 4, 8, 12 and 24-hour outage duration.

Use it for the resilience-duration plot and reliability discussion.

## `individual_vs_shared.csv`

This file is not expected in the current normal run because:

```text
RUN_INDIVIDUAL_VS_SHARED = False
```

The study is intentionally disabled until distinct household demand profiles are available.

---

# 16. Common KPI columns in the scenario CSV files

Most scenario files use the same KPI schema.

## Configuration

- `case`: scenario identifier
- `houses`: number of households
- `panel_count`: PV-module count
- `pv_kwp`: installed PV DC capacity
- `bess_modules`: number of battery modules
- `converter_kw`: inverter rating
- `grid_export_allowed`: whether export is enabled
- `grid_battery_charging_allowed`: should be false in normal community operation
- `islanded`: whether EPM grid exchange is disabled

## Load and reliability

- `load_kwh`: total load in the simulated period
- `served_load_kwh`: supplied load
- `unserved_energy_kwh`: energy not supplied
- `reliability_pct`: served load / total load

## PV and converter

- `pv_dc_generation_kwh`
- `pv_penetration_pct`
- `inverter_ac_output_kwh`
- `inverter_losses_kwh`

## Grid interaction

- `grid_import_kwh`
- `grid_export_kwh`
- `net_grid_exchange_kwh`
- `net_grid_balance_pct`
- `net_grid_independence_pct`
- `net_annual_exporter`
- `grid_import_hours`
- `grid_independent_hours_pct`
- `peak_import_kw`
- `peak_export_kw`

## Battery

- `battery_charge_kwh`
- `battery_discharge_kwh`
- `battery_cycle_energy_sum_kwh`
- `battery_throughput_kwh`

`battery_throughput_kwh` is the preferred HOMER-comparable cycling metric.

## Main autonomy KPI

- `self_sufficiency_pct`

This is the primary physical autonomy measure and is based on **gross grid imports**.

## Cost fields

- `capex_usd`
- `capex_plus_grid_import_cost_usd`
- `annualized_capex_usd`
- `annual_grid_import_cost_usd`
- `annual_grid_export_credit_usd`
- `annual_net_grid_cost_usd`
- `annual_grid_energy_cost_usd`
- `annual_battery_wear_cost_usd`
- `annualized_gross_cost_burden_usd`
- `annualized_total_cost_usd`
- `cost_per_load_kwh_usd`

For the design plots, the important field is:

```text
capex_plus_grid_import_cost_usd
```

Do not describe that field as NPC, LCOE or annualized system cost.

---

# 17. Pandapower handoff files

The reference case exports three files for the detailed grid model.

## `pandapower_handoff_S2_REFERENCE_PV_BESS.csv`

Shape in the current run:

```text
8,760 rows x 7 columns
```

Columns:

| Column | Meaning |
|---|---|
| `timestamp` | hourly timestamp |
| `pcc_import_positive_kw` | positive = import from EPM; negative = export |
| `pv_dc_kw` | PV DC production |
| `inverter_ac_output_kw` | inverter AC output |
| `load_kw` | community AC demand |
| `battery_dc_kw` | battery DC power; sign follows the handoff convention |
| `battery_soc_mwh` | PyPSA battery stored energy |

This file is the main time-series bridge between PyPSA and pandapower.

Pandapower can use it to identify both annual operation and critical snapshots.

## `pandapower_metadata_S2_REFERENCE_PV_BESS.csv`

Contains the physical network context:

- transformer 94022
- node 931076
- coordinates
- circuit 221-12
- MV/LV voltages
- transformer kVA
- conductor labels
- traced route lengths
- houses per branch
- timestamps of:
  - maximum import
  - maximum export
  - maximum AC inverter output
  - maximum load

For the current result set the critical timestamps are:

| Critical condition | Timestamp |
|---|---|
| Maximum grid import | `2025-09-03 19:00:00` |
| Maximum grid export | `2025-08-06 10:00:00` |
| Maximum AC inverter output | `2025-08-06 10:00:00` |
| Maximum load | `2025-09-01 19:00:00` |

These are useful pandapower study snapshots.

## `lv_branches_S2_REFERENCE_PV_BESS.csv`

Defines the household-to-radial-branch assignment.

For the reference four-house case:

```text
Branch 1: houses 1 and 2
Branch 2: houses 3 and 4
```

Pandapower uses this metadata to construct the explicit LV radial network that PyPSA intentionally does not model.

---

# 18. Model limitations

## 18.1 Synthetic hourly solar timing

Annual PV production is anchored strongly because it is calibrated to HOMER.

Exact hourly PV timing is less certain because the profile is reconstructed from monthly resource data and deterministic solar geometry rather than measured hourly irradiance.

Therefore:

- annual energy comparisons are strong,
- relative design trends are useful,
- exact hour-by-hour PV events should not be treated as observations.

Pandapower should therefore supplement the time-series critical hours with deterministic technical stress cases where appropriate.

## 18.2 Repeated household load shape

The demand series comes from HOMER monthly 24-hour profiles and is normalized to the final annual demand.

All houses use the same underlying normalized shape.

Consequently:

- the house-count sweep is a controlled scaling study,
- it is not a household-diversity study,
- the shared-versus-individual architecture study is deliberately disabled.

## 18.3 Aggregated electrical network

PyPSA has one aggregated community AC bus.

It does not represent:

- individual house voltage
- LV line impedance
- transformer equivalent impedance
- conductor thermal loading
- phase imbalance
- voltage regulation
- protection behavior

These belong to pandapower.

## 18.4 CAPEX extrapolation

Only the reference installed system has an actual quotation.

Alternative PV/BESS sizes use linear component scaling based on the HOMER component allocation, reconciled to the quotation subtotal.

Those alternatives are therefore **screening estimates**, not vendor prices.

## 18.5 Screening-cost time basis

`CAPEX + one year of grid import cost` intentionally combines two different time bases.

This was chosen as a simple workshop design-screening indicator.

It should not replace:

- net present cost
- levelized cost of electricity
- annualized lifecycle cost
- discounted cash-flow analysis

if a formal investment study is later required.

## 18.6 Grid dispatch coefficient

The 10 USD/kWh grid-import coefficient is not a tariff.

It exists only to force the desired local-first dispatch hierarchy.

Do not use it in economic reporting.

---

# 19. Current technical conclusions from v16

The v16 results support the following project conclusions.

### 1. Annual PV energy alone does not determine self-sufficiency

The reference array produces annual DC energy equal to **96.5% of annual load**, but PV-only operational self-sufficiency is only **43.06%** because generation and consumption do not occur at the same times.

### 2. Storage dramatically reduces gross grid dependence

Adding the four-module battery bank raises operational self-sufficiency from **43.06% to 85.38%**.

### 3. HOMER and PyPSA differ primarily because of battery dispatch

HOMER battery throughput is **17.745 kWh/year** versus approximately **3471 kWh/year** in PyPSA.

This is why HOMER still imports large amounts of electricity despite almost matching annual load with annual PV production.

### 4. Gross-import self-sufficiency and net grid independence must both be reported

For the reference PyPSA case:

- operational self-sufficiency: **85.38%**
- net grid independence: **89.45%**

For the HOMER reference:

- derived operational self-sufficiency: **38.52%**
- derived net grid independence: **91.62%**

Neither metric should replace the other.

### 5. Three batteries are close to the annual-autonomy saturation point

At 12 panels:

- 3 BESS: **85.33%**
- 4 BESS: **85.38%**

The fourth battery gives almost no additional annual self-sufficiency.

The four-battery system remains the quoted reference and may still offer extra resilience margin.

### 6. The practical 12-panel design space does not reach 90% operational self-sufficiency

The current search finds 90%, 95% and 100% targets infeasible.

The limitation is therefore not a plotting issue. It follows from the current hardware bounds, hourly resource/demand alignment, conversion losses and storage constraints.

### 7. The reference system has strong short-duration outage resilience

Starting at 80% SOC:

- 4 h: 100% served
- 8 h: 100% served
- 12 h: 100% served
- 24 h: about **99.25% served**

This suggests good short-duration resilience but does not imply indefinite island operation.

---

# 20. Reproducing the notebook

Recommended environment:

```bash
pip install pypsa highspy pandas numpy matplotlib
```

Place the notebook beside the input files or use:

```text
project/
├── SanRafael_PyPSA_Scenarios.ipynb
├── SimulacionTampico1k(1).xml
├── Nasa Data(2).csv
├── data/
└── results/
    └── figures/
```

Then execute the notebook from top to bottom.

The final run cell:

1. generates input/profile plots,
2. builds HOMER context,
3. runs core cases,
4. generates HOMER-PyPSA comparison tables,
5. runs PV and BESS sweeps,
6. searches the design space,
7. calculates the Pareto frontier,
8. runs outage simulations,
9. saves CSV outputs,
10. exports the pandapower handoff.

Before accepting a result set, verify:

```text
annual four-house load             = 7,592 kWh
reference PV DC generation         = 7,326.3 kWh
reference PV panel count           = 12
maximum allowed PV panel count     = 12
reference battery bank             = 19.2 kWh nominal / 17.3 kWh usable
reference quoted subtotal          = 11,974.79 USD
grid charging of BESS              = disabled
```

---

# 21. Recommended use in the final project

Use PyPSA for:

- annual community energy balance
- local-first energy management
- gross grid-dependence assessment
- net grid exchange assessment
- PV/BESS sizing sensitivity
- self-sufficiency design screening
- battery-utilization analysis
- outage resilience
- production of realistic hourly operating points for pandapower

Use pandapower for:

- transformer loading and reverse flow
- LV/MV voltage profiles
- line and conductor loading
- radial household network representation
- technical stress cases
- spatial network visualization

The two models are complementary. PyPSA answers **how the energy system operates over time**. Pandapower answers **whether the electrical network can physically support those operating conditions**.

---

# 22. File checklist

A complete PyPSA result package should contain at least:

```text
SanRafael_PyPSA_Scenarios.ipynb

results/
├── homer_reference_context.csv
├── homer_pypsa_metric_alignment.csv
├── homer_pypsa_reference_energy_flows.csv
├── core_cases.csv
├── pv_panel_sweep.csv
├── bess_module_sweep.csv
├── self_sufficiency_candidates.csv
├── self_sufficiency_design_steps.csv
├── self_sufficiency_infeasible_targets.csv
├── outage_reference_case.csv
├── outage_reference_dispatch.csv
├── outage_duration_sweep.csv
├── pandapower_handoff_S2_REFERENCE_PV_BESS.csv
├── pandapower_metadata_S2_REFERENCE_PV_BESS.csv
├── lv_branches_S2_REFERENCE_PV_BESS.csv
└── figures/
    ├── input_monthly_load_profiles.png
    ├── input_monthly_solar_resource.png
    ├── pypsa_topology_4hh.png
    ├── homer_reference_energy_context.png
    ├── all_core_cases_self_sufficiency.png
    ├── house_sweep_energy_share.png
    ├── pv_sweep_capex_plus_grid_cost_vs_self_sufficiency.png
    ├── bess_sweep_capex_plus_grid_cost_vs_self_sufficiency.png
    ├── self_sufficiency_pareto_frontier.png
    ├── self_sufficiency_vs_grid_import_cost.png
    ├── self_sufficiency_incremental_combined_cost.png
    ├── homer_pypsa_metric_alignment.png
    ├── gross_vs_net_grid_independence.png
    ├── homer_pypsa_reference_energy_flows.png
    ├── homer_pypsa_battery_cycling.png
    ├── outage_dispatch.png
    ├── outage_battery_soc.png
    └── outage_duration_load_served.png
```

`individual_vs_shared.csv` and its figure are intentionally not part of the normal v16 output package.

---

## Final model status

The PyPSA portion is sufficiently developed for the current SEEDExchange study objective.

Further effort should primarily go into:

1. locking the accepted v16 result package,
2. preserving this documentation with the repository,
3. carrying the PyPSA hourly handoff into pandapower,
4. testing network voltage, line loading, transformer loading and reverse-power-flow conditions,
5. documenting the final combined PyPSA + pandapower conclusions.
