# Input data

reference/: community-level source metadata.
templates/: blank schemas only.
private/: user-local, ignored source data, NOT for GitLab.

household_points_template.csv: ONE georeferenced house/building per row. Required household_id, community, latitude, longitude. Optional coordinate_source and estimated_accuracy_m. If multiple households share a building, keep a documented mapping for demand and network analysis. Do not substitute one village centroid or interview respondent for a home.

appliance_demand_template.csv: each row is one appliance for one anonymous household with appliance, quantity, rated_watts, hours_per_day, days_per_week, source_note. Input assumptions must be explicitly labelled and based on the proper survey codebook. Output is an indicative mean-day estimate, not design peak or 8760-hour profile.

No raw survey names, phone numbers or precise linked identities in GitLab; use permitted IDs/aggregates.
