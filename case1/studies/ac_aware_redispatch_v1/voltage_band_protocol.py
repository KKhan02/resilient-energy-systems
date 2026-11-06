"""Documented AC voltage magnitude bands and pure postprocessing utilities.

These are research magnitude screens, not certification of time-duration-based
Colombian service voltage regulations. Never infer customer voltage power quality
from hourly balanced-equivalent outputs alone.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

BANDS = (
    ('national_magnitude_reference', 0.90, 1.10),
    ('historical_epm_nt13_magnitude_reference', 0.90, 1.05),
    ('engineering_target', 0.95, 1.05),
    ('original_strict_research', 0.97, 1.03),
)


def validate_limits(vmin: float, vmax: float):
    if not np.isfinite(vmin) or not np.isfinite(vmax) or not (0 < vmin < 1 < vmax < 2):
        raise ValueError('Voltage limits must be finite and straddle 1.0 pu')
    return float(vmin), float(vmax)


def reclassify_ac_hours(rows: pd.DataFrame, full_year_required: bool = False) -> pd.DataFrame:
    """Reclassify fixed AC operating points against alternate magnitude limits.

    Does not rerun Q selection or alter dispatch, SOC, cable inputs or PCC rules.
    A successful magnitude-only classification is not real-world compliance.
    """
    required={'status','min_v_pu','max_v_pu','max_trafo_pct','max_line_pct'}
    if missing:=required-set(rows.columns):
        raise ValueError('AC result missing columns: '+str(sorted(missing)))
    if full_year_required and len(rows)!=8760:
        raise ValueError('Full-year assertion requires exactly 8760 rows')
    conv=rows.status.astype(str).eq('CONVERGED')
    vmin=pd.to_numeric(rows.min_v_pu,errors='coerce')
    vmax=pd.to_numeric(rows.max_v_pu,errors='coerce')
    trafo=pd.to_numeric(rows.max_trafo_pct,errors='coerce')
    lines=pd.to_numeric(rows.max_line_pct,errors='coerce')
    valid=conv & np.isfinite(vmin) & np.isfinite(vmax) & np.isfinite(trafo) & np.isfinite(lines)
    thermal=valid & (trafo<=100+1e-4) & (lines<=100+1e-4)
    summaries=[]
    for name,lower,upper in BANDS:
        passed=thermal & (vmin>=lower-1e-6) & (vmax<=upper+1e-6)
        summaries.append(dict(band=name,v_min_pu=lower,v_max_pu=upper,
            hours_evaluated=int(len(rows)),converged_hours=int(conv.sum()),
            feasible_hours=int(passed.sum()),failure_or_unconverged_hours=int((~passed).sum()),
            full_year_verified=bool(len(rows)==8760 and passed.all()),
            note='Fixed P/Q operating points reclassified; no new power flow or control optimization'))
    return pd.DataFrame(summaries)
