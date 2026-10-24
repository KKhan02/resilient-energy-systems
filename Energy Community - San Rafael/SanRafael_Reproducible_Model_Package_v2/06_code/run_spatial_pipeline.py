"""
San Rafael spatial pipeline, end-to-end and reproducible
========================================================

Run from the extracted package root:

    python 06_code/run_spatial_pipeline.py

It will:
1. load the original 35-house satellite image;
2. load the house pixel coordinates;
3. generate candidate transformer groupings for 4,5,6,7,8 houses maximum;
4. create grouping overlays on the original satellite image;
5. read the digitized EPM primary/secondary trace point files;
6. convert trace lengths from pixels to metres using the stored EPM scale calibration;
7. export grouping tables and measured line-length tables.

The trace-point CSVs are part of the package. This keeps the manual/digitized
choices visible and reproducible instead of hiding them inside an interactive session.
"""

from pathlib import Path
import math
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SITE_IMAGE = ROOT / "01_raw_site" / "community_satellite_houses_1_35.jpg"
HOUSE_CSV = ROOT / "05_spatial_grouping" / "san_rafael_house_image_coordinates.csv"
PRIMARY_TRACE = ROOT / "05_spatial_grouping" / "primary_trace_points_94022.csv"
SECONDARY_TRACE = ROOT / "05_spatial_grouping" / "secondary_trace_points_94022.csv"
SCALE_CSV = ROOT / "05_spatial_grouping" / "scale_calibration.csv"
OUTPUT_DIR = ROOT / "08_generated_spatial"

def polyline_length_pixels(points):
    pts = np.asarray(points, dtype=float)
    d = np.diff(pts, axis=0)
    return float(np.sqrt((d*d).sum(axis=1)).sum())

def pixels_to_metres(length_px, scale_bar_px, scale_bar_m):
    return float(length_px) * float(scale_bar_m) / float(scale_bar_px)

def balanced_proximity_groups(points_xy, max_group_size):
    pts = np.asarray(points_xy, dtype=float)
    n = len(pts)
    k = math.ceil(n / max_group_size)

    overall = pts.mean(axis=0)
    first = int(np.argmin(((pts - overall)**2).sum(axis=1)))
    centres = [pts[first].copy()]

    while len(centres) < k:
        d2 = np.min(
            np.stack([((pts-c)**2).sum(axis=1) for c in centres], axis=1),
            axis=1
        )
        centres.append(pts[int(np.argmax(d2))].copy())

    centres = np.asarray(centres)
    labels = None

    for _ in range(100):
        slots = np.repeat(np.arange(k), max_group_size)
        slot_centres = centres[slots]
        cost = np.sqrt(((pts[:,None,:]-slot_centres[None,:,:])**2).sum(axis=2))
        _, cols = linear_sum_assignment(cost)
        new_labels = slots[cols]

        new_centres = centres.copy()
        for j in range(k):
            members = pts[new_labels == j]
            if len(members):
                new_centres[j] = members.mean(axis=0)

        if labels is not None and np.array_equal(labels, new_labels):
            break
        labels = new_labels
        centres = new_centres

    # stable numbering north-to-south, then west-to-east
    order = np.lexsort((centres[:,0], centres[:,1]))
    remap = {old:new+1 for new,old in enumerate(order)}
    numbered = np.array([remap[int(x)] for x in labels], dtype=int)

    numbered_centres = []
    for g in sorted(set(numbered)):
        numbered_centres.append(pts[numbered == g].mean(axis=0))
    return numbered, np.asarray(numbered_centres)

def create_group_case(image, houses, max_group_size, output_dir):
    pts = houses[["x_px","y_px"]].to_numpy(float)
    labels, centres = balanced_proximity_groups(pts, max_group_size)

    grouped = houses.copy()
    grouped["group_id"] = [f"T{x:02d}" for x in labels]

    # tables
    group_rows = []
    for group, sub in grouped.groupby("group_id"):
        group_rows.append({
            "group_id": group,
            "n_houses": len(sub),
            "house_ids": ",".join(map(str, sub["house_id"].tolist())),
            "transformer_x_px": float(sub["x_px"].mean()),
            "transformer_y_px": float(sub["y_px"].mean()),
            "transformer_rating_kva": 5.0,
            "inverter_rating_kw": 5.0,
            "pv_dc_kwp": 5.4,
        })
    pd.DataFrame(group_rows).to_csv(
        output_dir / f"grouping_max_{max_group_size}_houses.csv", index=False
    )

    # overlay
    fig, ax = plt.subplots(figsize=(14,9))
    ax.imshow(image)
    for group, sub in grouped.groupby("group_id"):
        cx, cy = sub[["x_px","y_px"]].mean().to_numpy()
        for _, h in sub.iterrows():
            ax.plot([cx,h.x_px],[cy,h.y_px], linewidth=1.1)
        ax.scatter([cx],[cy], marker="s", s=65)
        ax.text(cx+7, cy-7, f"{group} ({len(sub)})", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.75, ec="none"))
    ax.set_title(f"Candidate grouping, maximum {max_group_size} houses per transformer")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_dir / f"grouping_max_{max_group_size}_houses.png",
                dpi=180, bbox_inches="tight")
    plt.close(fig)

    return grouped

def measure_traces(output_dir):
    scales = pd.read_csv(SCALE_CSV).set_index("calibration_id")
    primary = pd.read_csv(PRIMARY_TRACE)[["x_px","y_px"]].to_numpy(float)
    secondary = pd.read_csv(SECONDARY_TRACE)[["x_px","y_px"]].to_numpy(float)

    p_px = polyline_length_pixels(primary)
    s_px = polyline_length_pixels(secondary)

    p = scales.loc["primary_100m_map"]
    s = scales.loc["secondary_30m_map"]

    result = pd.DataFrame([
        {
            "section":"Primary local branch",
            "conductor":"#2 ACSR",
            "length_px":p_px,
            "scale_bar_px":p.scale_px,
            "scale_bar_m":p.scale_m,
            "length_m":pixels_to_metres(p_px,p.scale_px,p.scale_m),
            "status":"image-derived approximate",
        },
        {
            "section":"Secondary traced route",
            "conductor":"1/0 AAC",
            "length_px":s_px,
            "scale_bar_px":s.scale_px,
            "scale_bar_m":s.scale_m,
            "length_m":pixels_to_metres(s_px,s.scale_px,s.scale_m),
            "status":"user-traced, image-derived approximate",
        }
    ])
    result.to_csv(output_dir / "measured_line_lengths.csv", index=False)
    return result

def main():
    for path in [SITE_IMAGE,HOUSE_CSV,PRIMARY_TRACE,SECONDARY_TRACE,SCALE_CSV]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    image = Image.open(SITE_IMAGE)
    houses = pd.read_csv(HOUSE_CSV)

    summary = []
    for nmax in range(4,9):
        grouped = create_group_case(image, houses, nmax, OUTPUT_DIR)
        sizes = grouped.groupby("group_id").size().tolist()
        summary.append({
            "max_houses_per_transformer": nmax,
            "n_transformers": grouped["group_id"].nunique(),
            "group_sizes": ",".join(map(str,sizes)),
        })

    pd.DataFrame(summary).to_csv(
        OUTPUT_DIR / "grouping_sweep_summary.csv", index=False
    )

    lengths = measure_traces(OUTPUT_DIR)

    print("Spatial pipeline complete.")
    print("Outputs:", OUTPUT_DIR)
    print(pd.DataFrame(summary).to_string(index=False))
    print()
    print(lengths[["section","conductor","length_m"]].to_string(index=False))

if __name__ == "__main__":
    main()
