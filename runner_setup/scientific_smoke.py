"""Synthetic checks only; no scientific project inputs or production outputs."""
import importlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import sys
import traceback

out = Path("runner-test")
out.mkdir(exist_ok=True)
report = {"commit": os.environ.get("CI_COMMIT_SHA"), "python": platform.python_version(),
          "runner_id": os.environ.get("CI_RUNNER_ID"), "versions": {}, "checks": {}}
def check(name, fn):
    try:
        report["checks"][name] = {"status": "PASS", "result": fn()}
    except Exception as exc:
        traceback.print_exc()
        report["checks"][name] = {"status": "FAIL", "error": str(exc)}
def imports():
    expected = {"numpy":"2.3.4","pandas":"2.3.3","scipy":"1.16.3","pandapower":"3.4.0",
        "pypsa":"1.2.4","pvlib":"0.15.0","highspy":"1.14.0","numba":"0.64.0",
        "matplotlib":"3.10.7","pytest":"9.0.2","linopy":"0.8.0","pyomo":"6.10.0",
        "simbench":"1.6.1","lightsim2grid":"0.12.2","geopandas":"1.1.2",
        "rasterio":"1.5.0","shapely":"2.1.2","pyproj":"3.7.2"}
    mismatches = []
    for package, version in expected.items():
        importlib.import_module(package)
        actual = md.version(package)
        report["versions"][package] = actual
        if actual != version: mismatches.append(f"{package}: {actual} != {version}")
    if report["python"] != "3.12.9": mismatches.append("Python version differs")
    if mismatches: raise ValueError("; ".join(mismatches))
    return len(expected)
def numerical():
    import numpy as np
    x = np.linalg.solve([[3., 1.], [1., 2.]], [9., 8.])
    np.testing.assert_allclose(x, [2., 3.], atol=1e-12)
    return x.tolist()
def powerflow():
    import pandapower as pp
    net = pp.create_empty_network()
    a = pp.create_bus(net, vn_kv=20)
    b = pp.create_bus(net, vn_kv=20)
    pp.create_ext_grid(net, a, vm_pu=1.)
    pp.create_line_from_parameters(net, a, b, length_km=1., r_ohm_per_km=.2,
        x_ohm_per_km=.3, c_nf_per_km=0., max_i_ka=.4)
    pp.create_load(net, b, p_mw=1., q_mvar=.2)
    pp.runpp(net, numba=False)
    v = float(net.res_bus.at[b, "vm_pu"])
    loss = float(net.res_line.pl_mw.sum())
    assert net.converged and .99 < v < 1. and 0 < loss < .01
    return {"converged": bool(net.converged), "load_bus_vm_pu": v, "line_loss_mw": loss}
def optimization():
    import pypsa
    import pandas as pd
    import numpy as np
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(2))
    n.add("Carrier", "electricity")
    n.add("Bus", "b", carrier="electricity")
    n.add("Generator", "g", bus="b", carrier="electricity", p_nom=10., marginal_cost=20.)
    n.add("Load", "l", bus="b", p_set=[3., 5.])
    status, condition = n.optimize(solver_name="highs", solver_options={"threads": 1})
    dispatch = n.generators_t.p["g"].to_numpy()
    np.testing.assert_allclose(dispatch, [3., 5.], atol=1e-8)
    assert status == "ok" and condition == "optimal"
    assert abs(float(n.objective) - 160.) < 1e-8
    return {"status": status, "termination": condition, "dispatch_mw": dispatch.tolist(), "objective": float(n.objective)}
def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0,1], [3,5], marker="o")
    ax.set(xlabel="Synthetic time step", ylabel="Dispatch (MW)", title="Runner diagnostic only")
    fig.savefig(out / "synthetic_dispatch.png", dpi=120)
    plt.close(fig)
    assert (out / "synthetic_dispatch.png").stat().st_size > 0
    return "synthetic_dispatch.png"
for name, fn in [("versions_and_imports", imports), ("numpy", numerical), ("pandapower", powerflow), ("pypsa_highs", optimization), ("plot", plot)]:
    check(name, fn)
report["status"] = "PASS" if all(x["status"] == "PASS" for x in report["checks"].values()) else "FAIL"
(out / "scientific_diagnostic.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SCIENTIFIC_DIAGNOSTIC_JSON", json.dumps(report), flush=True)
sys.exit(report["status"] != "PASS")
