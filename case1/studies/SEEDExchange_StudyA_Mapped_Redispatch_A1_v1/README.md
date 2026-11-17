# Study A mapped-feeder redispatch, A1 exploratory AC trial (16 November 2026)

## Evidence already audited, without running new models

Input: `StudyA_Mapped_SOC_Windows_for_Redispatch.zip`, SHA-256 `571ab9deba6b16fce357868b8848762a975c5761d218ba5e9544b409133e0a66`.

- 175 unique mapped-network, design-dispatch/timestamp constraint events: 19 A1 and 156 A0.
- 16 individually signed full-year source schedules, 5,075 window rows of 29 hours per event.
- At all 175 events, an earlier same-day hour within the previous 8 hours has at least 0.15 kW of DC battery discharge. This **does not** show the discharge is available to shift safely.
- All 19 A1 failure-hour end-SOC values equal their signed model's operational floor: 0.229 kWh per battery module of the represented usable-energy state. They are **not** 20% of the nameplate energy value itself.
- Source groups for this first AC trial: 8 A1 energy/dispatch schedules, 19 design-dispatch event records (5 unique calendar hours at A1 94022, two at 113699, two at 106039 causal).
- Original A1 106039 optimized source schedules **are already corrected and excluded**. A0 cases and the proposed 92395 MST are not corrected by this script.

See `INDEPENDENT_WINDOW_QA.json`, `A1_19_EVENT_CANDIDATE_REGISTER.csv`, `16_MAPPED_SCHEDULE_TRIAGE.csv` and `ALL_175_ENERGY_DONOR_PRECHECK.csv`.

## Procedure (Windows Miniforge/Anaconda Prompt)

Extract **this package** into your GitLab checkout's `case1\studies\` directory, preserving its directory name. The original verified SOC-window ZIP is bundled inside this package. The trial uses that identical source by default. You do not need to copy a second ZIP to the checkout root. Run the following commands **from the checkout root**, with the existing study dependencies installed.

First verify the ZIP without invoking the numerical simulator:

```bat
python -m unittest discover -s "case1\studies\SEEDExchange_StudyA_Mapped_Redispatch_A1_v1\tests" -v
python "case1\studies\SEEDExchange_StudyA_Mapped_Redispatch_A1_v1\a1_repair_trial.py" --preflight
```

Optional narrow first physical AC trial for the A1 94022 higher-SS optimized source (one failing date):

```bat
python "case1\studies\SEEDExchange_StudyA_Mapped_Redispatch_A1_v1\a1_repair_trial.py" --repo-root . --only-case A1_94022_ss90_ref --only-dispatch optimized --out "StudyA_A1_94022_OneCase_Trial" --zip-out "StudyA_A1_94022_OneCase_Trial.zip"
```

For all remaining **eight** A1 design-dispatch schedules, use **new** output paths:

```bat
python "case1\studies\SEEDExchange_StudyA_Mapped_Redispatch_A1_v1\a1_repair_trial.py" --repo-root . --out "StudyA_A1_Mapped_Redispatch_Trial_v1" --zip-out "StudyA_A1_Mapped_Redispatch_Trial_v1.zip"
```

Upload `StudyA_A1_Mapped_Redispatch_Trial_v1.zip` here for independent audit, **even if it reports unresolved violations**. The script does not modify existing signed source files or the 432 original annual AC results.

### What the trial does and does not do

1. Verifies source annual energy, causal results, hardware, input manifest and full 8,760-hour AC summaries, SHA-256 and identity.
2. For each A1 event, considers shifts from a previous same-day discharge hour. Candidate DC power movements are bounded to 0.15–2.50 kW and must preserve annual battery SOC, battery/inverter limits, demand coverage, no export, no unserved load, total annual imports, PV curtailment and year-end SOC.
3. Independently solves **both** donor and target hours for all nine PF (0.95/0.98/1.00) and feeder-length (1.0/1.3/1.6) settings. It first replays the unchanged original to ensure the new solver matches archived signed AC results.
4. Only accepts a proposed shift if **both** times pass all nine settings. If none passes, records the event as unresolved. At the end, replays all changed hours and reuses verified unchanged-hour AC results across the complete 2025 annual records.
5. Creates an **exploratory fixed-hardware candidate**, not a PyPSA optimum and not a dynamic controller or proof of field compliance. It does not improve annual PV utilization, change curtailment, alter equipment size, or account for AC-loss cost differences.

Output includes `TRIAL_MANIFEST.json`, `ADOPTED_SHIFT_EVENTS.csv`, `UNRESOLVED_EVENTS.csv`, `NINE_FACTOR_ANNUAL_REUSE.csv`, `CHANGED_HOURS_FINAL_AC.csv`, and candidate 8,760-hour schedule CSVs for the groups with accepted shifts.

**Important:** If the original source or baseline AC validation fails, the script stops. Do not weaken those checks to force a result. This package was checked on uploaded SOC-window records and seven synthetic unit tests; **the physical AC trial itself has not yet been executed here**.

## After this stage

- If all A1 cases pass, update the portfolio status register by a new independent overlay, never overwrite historical baseline.
- If an event does not pass, examine why: feeder voltage response, donor-hour headroom, unavailable stored energy or equipment limits. Do not automatically assume another battery is required.
- A0 94022 and 106039 have more overlapping evening hours. Plan a **day-wise or annual SOC-constrained optimization** across interacting violation times and AC-P sensitivities rather than applying independent shifts.
- A0 92395 MST remains a separate Study B conductor/routing and siting problem. PV/BESS marginal capacity and curtailed-energy reuse should be compared only after AC constraints are reconciled.
