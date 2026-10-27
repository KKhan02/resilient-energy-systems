# Conditional 94022 AC results from GitLab CI

Test and simulation job: https://gitlab.com/KKhan02/resilient-energy-systems/-/jobs/17513000800. These are **new solved** pandapower snapshot results, not historic v5 results. No new transformer was introduced. No customer-to-transformer assignment is utility certified.

- 36 cases across two hypothetical link geometries, central/2 shared injection sites, and solar/storage power sensitivities. 31 meet both 0.97–1.03 pu voltage and nominal equipment loading screens; 5 do not.
- Rectilinear no-DER peak has minimum LV voltage **0.967372 pu** and 94022 transformer loading **86.608655%**. This misses the lower-screen voltage threshold with no battery dispatch.
- Matched 2 kW evening discharge: centralized minimum **0.975011 pu**, two-shared-site minimum **0.978396 pu**. This is an *instantaneous* impact only.
- Rectilinear 5.22 kWp DC, unrestricted midday PV: central maximum LV voltage **1.0063 pu**, shared-two-sites maximum **1.036931 pu**. Shared-site voltage exceeds the model's upper screening bound.
- With gross-load-capped PV export proxy (not an exact operational PCC controller), the shared-two-sites 5.22 kWp case has max voltage **1.004295 pu** in this hour.

These results **do not establish** a real feeder, a permitted PV export capacity, 8760-hour battery availability, or lifecycle economic superiority. Two distinct 5 kW equivalent settings cannot be implicitly pooled with other EPM low-voltage territories. The modeled seven service links each originate independently at 94022; no real common trunk, service cable length or meter has been verified. Source stochastic profiles are not actual metered household consumption. For full PV+BESS sizing, next run annual time-coupled energy/battery SOC, additional existing EPM service territories with verified locations/nameplates, and a consistent 25-year cost model.
