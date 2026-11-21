# SEEDExchange Study A | Reverse 113699 matched-hardware pilot audit

**21 November 2026 | Independently inspected GitLab commit 4cffd500**

- Input: signed A0 113699 hardware on A1 six-house membership H03,H04,H05,H06,H07,H10, versus original A0 four-house H04,H05,H07,H10. Fixed hardware: 17 PV panels (7.395 kWp), 3 battery modules, battery DC limit 4.7009394509 kW, 5 kVA inverter and assumed 3 kVA transformer.
- Manifest status: ENERGY_ONLY_REVERSE_MATCHED_HARDWARE_PASS_AC_PENDING. Exactly one completed case, no errors, zero new AC.
- Independently read the full 8,760-hour 2025 CSV, duplicate case receipt and summary. 8,760 consecutive distinct timestamps and all numeric entries finite.
- Byte-integrity audit: GitLab LF SHA-256 68d7a0eee6a4c04720b948374cb83b05f8f46f3a7f99e5e53aa38026f40dbb1d; restoring original Windows CRLF yields the signed CSV hash df1952e61da8404677cceed1c760c5be1a5c891855f6dd8968088136997112d8. Pinned Git-normalized run manifest hash 5b2c37514608845490843e502466351dc0b7124f6833b9b42e6e407225ce2e8d.
- Measured annual sums: demand 11,388.000000003 kWh, import 3,682.545919229 kWh, PV DC available 8,979.832381835 kWh, PV DC used 8,289.923347780 kWh, curtailed 689.909034057 kWh, battery DC charge 3,578.381044661 kWh, discharge 3,399.461992427 kWh. Self-sufficiency 67.662926596%. Annual equipment+grid purchase USD 2,481.192672.
- Zero exported and unserved energy; no simultaneous battery charging/discharging; no battery or inverter power limit violations. SOC 0.687 to 12.975 kWh within physical 20% floor and model upper bound. Max cyclic SOC residual 1.409e-10 kWh. Max AC active power balance and PV availability closure residual each ~1e-10 kW. Max PCC apparent-power proxy 2.877529620 kVA, below assumed 3 kVA.
- Compared with original A0 four-home source using the identical equipment: demand 7,592 kWh, import 797.255512 kWh, PV DC curtailment 1,627.129565 kWh, annual equipment+imports USD 1,644.458454. This changed-house-count comparison alone does not establish geographic superiority.
- **Limitation:** Optimal fixed-hardware energy result only. No new pandapower annual AC, conductor voltage/loading, losses, field topology, EPM approval or physical transformer confirmation.

The full reciprocal 16-case runner can now reuse this exact pinned reverse pilot along with the first forward pilot and two same-hardware 106039 original energy schedules. Remaining annual 8,760-hour fixed-hardware LP solves: 12. No new equipment investment MILP or AC run is authorized by this audit. Full local synthetic tests and preflight still pending; do not claim the eight matched 34-house portfolio results until local full solve and remote audit.
