from __future__ import annotations
import json
from pathlib import Path
import lightkurve as lk
import numpy as np
import pandas as pd

TARGET = "Kepler-10"
OUTPUT = Path("data/demo/kepler10_q17_longcadence.csv")


def main():
    result = lk.search_lightcurve(TARGET, mission="Kepler")
    table = result.table
    exposures = np.asarray(table["exptime"], dtype=float)
    descriptions = [str(x) for x in table["description"]]
    choices = [i for i, desc in enumerate(descriptions) if exposures[i] > 1000 and "Q17" in desc]
    if not choices:
        choices = list(np.flatnonzero(exposures > 1000))
    if not choices:
        raise RuntimeError("MAST did not return a Kepler long-cadence product for Kepler-10.")
    index = int(choices[0])
    lc = result[index].download()
    if lc is None:
        raise RuntimeError("MAST returned no data for the selected public Kepler product.")
    frame = pd.DataFrame({"time": lc.time.value, "flux": lc.flux.value})
    if getattr(lc, "flux_err", None) is not None:
        frame["flux_err"] = lc.flux_err.value
    if getattr(lc, "quality", None) is not None:
        frame["quality"] = lc.quality
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False, float_format="%.10g")
    row = table[index]
    meta = {
        "target": TARGET,
        "mission": "Kepler",
        "source": "NASA MAST via Lightkurve",
        "archive_product_filename": str(row["productFilename"]),
        "author": str(row["author"]),
        "exposure_seconds": float(row["exptime"]),
        "description": str(row["description"]) if "description" in table.colnames else "",
        "license": "Public NASA mission data; cite MAST and the original Kepler mission.",
        "time_column": "time (Lightkurve Time.value; BJD offset/time format as encoded by source)",
        "flux_column": "flux (source product units; unnormalized)",
        "rows": len(frame),
    }
    OUTPUT.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
