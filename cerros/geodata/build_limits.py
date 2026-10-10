"""Builds cerros/geodata/limits.json.gz, the boundaries used to suggest a
mountain's country and region from its coordinates (cerros/geo.py).

Not needed to run the site: the result is already in the repo. Run it again
only to update the maps, with shapely installed and these two files downloaded
next to this script:

  Chile, regions and the international border, from the Biblioteca del Congreso
  Nacional (BCN) via geoBoundaries, CC BY 3.0 IGO:
    https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/CHL/ADM1/geoBoundaries-CHL-ADM1_simplified.geojson
  Argentina, Bolivia and Peru (provinces / departments), Natural Earth 1:10m,
  public domain, approximate (errors of 1 to 3 km):
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson

  python cerros/geodata/build_limits.py
"""
import base64
import gzip
import json
from itertools import combinations
from pathlib import Path

import shapely
from shapely.geometry import box, shape
from shapely.ops import unary_union

HERE = Path(__file__).parent
CHILE_FILE = HERE / "geoBoundaries-CHL-ADM1_simplified.geojson"
NE_FILE = HERE / "ne_10m_admin_1_states_provinces.geojson"
OUT = HERE / "limits.json.gz"

NEIGHBOURS = {"ARG": "Argentina", "BOL": "Bolivia", "PER": "Perú"}
NEAR_CHILE = 1.5  # degrees (~150 km): neighbour provinces kept around Chile
SIMPLIFY = 0.0003  # degrees (~30 m) for the BCN maps


def fix_text(text):
    # geoBoundaries' Chilean names come double-encoded ("RegiÃ³n").
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def packed(geom):
    """Geometry as base64 WKB, coordinates rounded to 5 decimals (~1 m): loads
    fast and with little memory (no Python objects per coordinate)."""
    return base64.b64encode(shapely.to_wkb(shapely.set_precision(geom, 0.00001))).decode()


def shared_line(a, b):
    line = a.boundary.intersection(b.buffer(0.0005))
    return line if not line.is_empty and line.length > 0.001 else None


def main():
    chile = []
    for f in json.loads(CHILE_FILE.read_text(encoding="utf-8"))["features"]:
        geom = shape(f["geometry"]).buffer(0).simplify(SIMPLIFY, preserve_topology=True)
        chile.append({"country": "Chile", "region": fix_text(f["properties"]["shapeName"]), "geom": geom})
    chile_all = unary_union([a["geom"] for a in chile])

    minx, miny, maxx, maxy = chile_all.bounds
    near = box(minx - NEAR_CHILE, miny - NEAR_CHILE, maxx + NEAR_CHILE, maxy + NEAR_CHILE)
    hull = chile_all.convex_hull.buffer(NEAR_CHILE)
    ne_features = [
        f for f in json.loads(NE_FILE.read_text(encoding="utf-8"))["features"]
        if f["properties"].get("adm0_a3") in NEIGHBOURS
    ]
    neighbours = []
    for f in ne_features:
        p = f["properties"]
        geom = shape(f["geometry"]).buffer(0)
        if not geom.intersects(near) or not geom.intersects(hull):
            continue
        # Only the part near Chile matters (keeps the file small).
        geom = geom.intersection(hull)
        if not geom.intersects(near):
            continue
        # Chile's side of the border comes from BCN, not from Natural Earth.
        geom = geom.difference(chile_all)
        if geom.is_empty:
            continue
        neighbours.append(
            {"country": NEIGHBOURS[p["adm0_a3"]], "region": p.get("name_es") or p["name"], "geom": geom}
        )

    limits = []
    # Chile's international border, precise (BCN).
    for code, country in NEIGHBOURS.items():
        side = unary_union([a["geom"] for a in neighbours if a["country"] == country])
        if side.is_empty:
            continue
        line = chile_all.boundary.intersection(side.buffer(0.25))
        if not line.is_empty:
            limits.append({"label": f"Chile – {country}", "precise": True, "geom": line})
    # Between Chilean regions, precise (BCN).
    for a, b in combinations(chile, 2):
        line = shared_line(a["geom"], b["geom"])
        if line is not None:
            limits.append({"label": f"{a['region']} – {b['region']}", "precise": True, "geom": line})
    # Between neighbouring provinces, approximate (Natural Earth).
    for a, b in combinations(neighbours, 2):
        line = shared_line(a["geom"], b["geom"])
        if line is not None:
            limits.append({"label": f"{a['region']} – {b['region']}", "precise": False, "geom": line})

    data = {
        "sources": {
            "Chile": "Biblioteca del Congreso Nacional (BCN), vía geoBoundaries (CC BY 3.0 IGO)",
            "vecinos": "Natural Earth 1:10m (dominio público), aproximado",
        },
        "areas": [{"country": a["country"], "region": a["region"], "precise": a["country"] == "Chile",
                   "wkb": packed(a["geom"])} for a in chile + neighbours],
        "limits": [{"label": l["label"], "precise": l["precise"], "wkb": packed(l["geom"])} for l in limits],
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{OUT.name}: {len(data['areas'])} areas, {len(data['limits'])} limits, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
