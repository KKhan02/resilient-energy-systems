# Evidence review, signed uploaded A1 106039 event-hour archive

Source: `StudyA_A1_106039_Event_Hour_SOC_Evidence.zip`, containing four signed optimized/causal annual-source excerpts (14 days each), five signed 8,760-hour AC-source excerpts and 8 event SOC records. Each input excerpt's source signature was supplied by the extractor. This review directly checked the records in the uploaded ZIP. No new power-flow calculations were performed.

## Event record

### November 27, 2025, 20:00

- All four energy/causal hardware/operation cases report aggregate demand **4.843887 kW**, grid import equal to demand and **zero inverter output**.
- Both hardware tiers in both operation modes report **1.832000 kWh after-hour usable SOC**, the physical-floor equivalent in the energy model. At 19:00 the battery was already at the same floor.
- Optimized minimum-cost tier at 18:00 delivered 1.772273 kW AC from 1.866 kW DC battery output, reaching the floor. Higher-SS tier at 18:00 delivered 3.979375 kW AC from 4.189 kW DC battery output, also reaching the floor.
- Modelled AC: PF.98 length1.0 gives **103.491672% transformer loading**, 0.959731 pu minimum household voltage; PF.95 length1.6 gives **107.431169%** transformer loading, 0.954236 pu minimum voltage. Q controller is `Q_OFF` at the evening event.

### October 13, 2025, 20:00

- Minimum-cost optimized/causal case at the event has 0.256078 kW inverter output and after-hour SOC 1.832 kWh. Under PF.95 length1.6, transformer loading is **103.195603%**, minimum voltage 0.956580 pu.
- Higher-SS case supplies 4.889357 kW AC to cover demand that hour, and its SOC remains 4.165928 kWh after the hour. No analogous overload for the higher-SS tier is present in the AC excerpts.
- Minimum-cost equipment at **17:00** has 2.830 kW battery DC output and energy comfortably above minimum. The trial can reserve some of this without reducing service at the event.

## Finding

The event-hour failures are energy-timing/SOC constraints, not evidence of insufficient nameplate battery discharge power. Reserve small discharge energy from earlier same-day hours and revalidate all modified hours in the original EPM AC solver before declaring success. The trial code is separate and does not alter historical results.
