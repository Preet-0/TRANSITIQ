from __future__ import annotations
import lightkurve as lk


def search_observations(target, mission="Kepler"):
    res = lk.search_lightcurve(target, mission=mission)
    rows = []
    columns = set(res.table.colnames)
    for i, row in enumerate(res.table):

        def field(key, fallback=""):
            return str(row[key]) if key in columns else fallback

        description = field("description")
        quarter = field("quarter")
        sector = field("sector")
        if not quarter:
            import re

            match = re.search(r"\bQ(?:uarter)?\s*0*(\d+)\b", description, re.IGNORECASE)
            quarter = match.group(1) if match else ""
        if not sector:
            import re

            match = re.search(r"\bSector\s*0*(\d+)\b", description, re.IGNORECASE)
            sector = match.group(1) if match else ""
        rows.append(
            {
                "index": i,
                "mission": field("mission"),
                "author": field("author"),
                "exposure": field("exptime"),
                "sector": sector,
                "quarter": quarter,
                "product": field("productFilename"),
                "target": field("target_name"),
                "description": description,
            }
        )
    return res, rows


def download_observation(results, index):
    lc = results[int(index)].download()
    if lc is None:
        raise RuntimeError("MAST returned no downloadable light curve for the selected product.")
    time = lc.time.value
    flux = lc.flux.value
    err = lc.flux_err.value if getattr(lc, "flux_err", None) is not None else None
    quality = lc.quality
    return time, flux, err, quality
