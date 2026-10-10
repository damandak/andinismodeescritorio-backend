"""Country and region of a point, from the maps in cerros/geodata/limits.json.gz.

Chile (regions and the international border) comes from the Biblioteca del
Congreso Nacional and is precise to a few tens of metres. Neighbouring
provinces come from Natural Earth and can be off by 1 to 3 km, so their limits
get an extra safety margin (APPROX_ERROR).

A mountain is "confident" when it is at least `margin` metres from every limit
(plus APPROX_ERROR for the approximate ones): coordinates a little off, or a
summit right on the border, can't put it on the wrong side.

The maps are loaded the first time they are needed and kept in memory.
"""
import gzip
import json
import math
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "geodata" / "limits.json.gz"
DEFAULT_MARGIN = 2000  # metres
APPROX_ERROR = 3000  # metres, for Natural Earth limits
METRES_PER_DEGREE = 111_320


@dataclass
class Place:
    country: str
    region: str


@dataclass
class Suggestion:
    place: Place | None  # where the point falls (None: outside the maps)
    distance: int | None = None  # metres to the nearest limit
    limit: str = ""  # that limit, e.g. "Chile – Argentina"
    confident: bool = False  # far enough from every limit
    across: list = field(default_factory=list)  # places on the other side of near limits

    def describe(self):
        if not self.place:
            return "Fuera de los mapas disponibles (Chile y provincias vecinas)."
        text = f"{self.place.country}, {self.place.region}."
        if self.distance is not None:
            text += f" A {format_distance(self.distance)} del límite {self.limit}."
        return text


def format_distance(metres):
    if metres < 1000:
        return f"{metres} m"
    return f"{metres / 1000:.1f} km".replace(".", ",")


@lru_cache(maxsize=1)
def _maps():
    import base64

    from shapely import STRtree, from_wkb

    data = json.loads(gzip.decompress(DATA_FILE.read_bytes()))
    geom = lambda item: from_wkb(base64.b64decode(item["wkb"]))
    areas = [(Place(a["country"], a["region"]), geom(a)) for a in data["areas"]]
    limits = [(l["label"], l["precise"], geom(l)) for l in data["limits"]]
    del data
    return {
        "areas": areas,
        "area_tree": STRtree([g for _, g in areas]),
        "limits": limits,
        "limit_tree": STRtree([g for _, _, g in limits]),
    }


def release_maps():
    """Free the maps (the web process loads them only for a moment) and give
    the memory back to the system (glibc keeps freed memory otherwise)."""
    import gc

    _maps.cache_clear()
    gc.collect()
    try:
        import ctypes

        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


def _to_metres(lat):
    """Function that turns lon/lat into local metres around latitude `lat`."""
    kx = METRES_PER_DEGREE * math.cos(math.radians(lat))

    def project(coords):
        out = coords.copy()
        out[:, 0] *= kx
        out[:, 1] *= METRES_PER_DEGREE
        return out

    return project


def suggest(latitude, longitude, margin=DEFAULT_MARGIN):
    """Where (lat, lon) falls and how close it is to a limit."""
    import shapely
    from shapely.geometry import Point, box

    maps = _maps()
    lat, lon = float(latitude), float(longitude)
    point = Point(lon, lat)
    project = _to_metres(lat)
    here = shapely.transform(point, project)

    def metres(geom):
        return here.distance(shapely.transform(geom, project))

    # Area containing the point; in the gaps between the two map sources (a few
    # hundred metres along the border) the nearest one within 5 km.
    place = None
    for i in maps["area_tree"].query(point, predicate="intersects"):
        place = maps["areas"][i][0]
        break
    if place is None:
        nearest = maps["area_tree"].nearest(point)
        if nearest is not None and metres(maps["areas"][nearest][1]) <= 5000:
            place = maps["areas"][nearest][0]
    if place is None:
        return Suggestion(place=None)

    # Limits near enough to matter.
    reach = margin + APPROX_ERROR + 5000
    deg_y = reach / METRES_PER_DEGREE
    deg_x = deg_y / max(math.cos(math.radians(lat)), 0.1)
    window = box(lon - deg_x, lat - deg_y, lon + deg_x, lat + deg_y)
    best = None
    confident = True
    for i in maps["limit_tree"].query(window):
        label, precise, geom = maps["limits"][i]
        d = metres(geom)
        if d < margin + (0 if precise else APPROX_ERROR):
            confident = False
        if best is None or d < best[0]:
            best = (d, label)

    across = []
    if not confident:
        for i in maps["area_tree"].query(window):
            other, geom = maps["areas"][i]
            if other != place and other not in across and metres(geom) < margin + APPROX_ERROR:
                across.append(other)

    if best is None:
        return Suggestion(place=place, confident=True)
    return Suggestion(place=place, distance=round(best[0]), limit=best[1], confident=confident, across=across)


# --- Matching the map's names with the countries and regions in the database ---

STOPWORDS = {"region", "de", "del", "la", "las", "los", "el", "y", "provincia", "departamento"}


def name_key(name):
    """Words of a name without accents, case, hyphens or filler words:
    "Región del Bío-Bío" -> {"biobio"}, "O'Higgins" -> {"ohiggins"}."""
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    text = text.replace("-", "").replace("'", "").replace("’", "")
    words = "".join(c if c.isalnum() else " " for c in text).split()
    return frozenset(w for w in words if w not in STOPWORDS)


def same_name(a, b):
    """True when one name's words contain the other's: "Metropolitana" matches
    "Región Metropolitana de Santiago", "Aysén" matches "Región de Aysén del…"."""
    ka, kb = name_key(a), name_key(b)
    return bool(ka) and bool(kb) and (ka <= kb or kb <= ka)


def find_in_database(place, countries, regions):
    """(Country, Region) from the database for a map place; None when missing
    or ambiguous. `countries` and `regions` are lists of model instances."""
    if place is None:
        return None, None
    country_matches = [c for c in countries if name_key(c.name) == name_key(place.country)]
    country = country_matches[0] if len(country_matches) == 1 else None
    region_matches = [
        r for r in regions
        if same_name(r.name, place.region) and (country is None or r.country_id == country.pk)
    ]
    region = region_matches[0] if len(region_matches) == 1 else None
    return country, region
