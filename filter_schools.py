#!/usr/bin/env python3
"""
Filter Palisades_Malibu_Schools.geojson to fire-affected Palisades schools,
add fire_damage values, apply bounding-box filter, and save as
Palisades_Fire_Schools.geojson.
"""
import json
import sys

# Force UTF-8 output on Windows so print() doesn't crash on special chars.
sys.stdout.reconfigure(encoding="utf-8")

SOURCE = "Palisades_Malibu_Schools.geojson"
OUTPUT = "Palisades_Fire_Schools.geojson"

# Geographic bounding box - Pacific Palisades / Malibu fire zone only.
LAT_MIN, LAT_MAX =  33.95,  34.15
LON_MIN, LON_MAX = -118.65, -118.49

# Name search terms (case-insensitive partial match on name or label field).
SEARCH_TERMS = [
    "Calvary Christian",
    "Canyon Charter Elementary",
    "Corpus Christi",
    "Marquez Charter",
    "Palisades Charter Elementary",
    "Palisades Charter High",
    "Seven Arrows",
    "St. Matthew",
    "Village School",
    "Topanga Elementary",
]

# fire_damage assignment rules - checked in order, first match wins.
FIRE_DAMAGE_RULES = [
    ("Palisades Charter Elementary", "moderate"),  # before generic "Palisades Charter"
    ("Palisades Charter High",       "major"),
    ("Calvary Christian",            "moderate"),
    ("Canyon Charter Elementary",    "minimal"),
    ("Corpus Christi",               "moderate"),
    ("Marquez Charter",              "major"),
    ("Seven Arrows",                 "moderate"),
    ("St. Matthew",                  "moderate"),
    ("Village School",               "moderate"),
    ("Topanga Elementary",           "minimal"),
]


def normalize(s):
    return (
        str(s or "")
        .replace("’", "'").replace("‘", "'")
        .replace("“", '"').replace("”", '"')
        .lower().strip()
    )


def get_display_name(props):
    return (props.get("name") or props.get("label") or "").strip()


def get_coords(feat):
    geom = feat.get("geometry") or {}
    coords = geom.get("coordinates", [None, None])
    return coords[0], coords[1]  # lon, lat


def in_bbox(lon, lat):
    if lon is None or lat is None:
        return False
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def matches_any_term(name_norm):
    return any(normalize(t) in name_norm for t in SEARCH_TERMS)


def assign_fire_damage(name_norm):
    for keyword, damage in FIRE_DAMAGE_RULES:
        if normalize(keyword) in name_norm:
            return damage
    return None


# -- Load ---------------------------------------------------------------------
with open(SOURCE, encoding="utf-8") as f:
    data = json.load(f)

total_features = len(data["features"])

# -- Match by name, then filter by bounding box -------------------------------
name_matched  = []
bbox_rejected = []
found_terms   = set()

for feat in data["features"]:
    p            = feat["properties"]
    display_name = get_display_name(p)
    name_norm    = normalize(display_name)

    if not matches_any_term(name_norm):
        continue

    lon, lat = get_coords(feat)

    if not in_bbox(lon, lat):
        bbox_rejected.append((display_name, lon, lat))
        continue

    damage           = assign_fire_damage(name_norm)
    p["fire_damage"] = damage
    name_matched.append(feat)

    for term in SEARCH_TERMS:
        if normalize(term) in name_norm:
            found_terms.add(term)

not_found = [t for t in SEARCH_TERMS if t not in found_terms]

# -- Save ---------------------------------------------------------------------
out_fc = {"type": "FeatureCollection", "features": name_matched}
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(out_fc, f, ensure_ascii=False, indent=2)

# -- Summary ------------------------------------------------------------------
print(f"Source : {SOURCE}  ({total_features} total features)")
print(f"Output : {OUTPUT}")
print(f"Bbox   : lat [{LAT_MIN}, {LAT_MAX}]  lon [{LON_MIN}, {LON_MAX}]")
print()

print(f"-- Matched and kept: {len(name_matched)} school(s) " + "-" * 30)
all_in_bbox = True
for feat in name_matched:
    p            = feat["properties"]
    display_name = get_display_name(p)
    lon, lat     = get_coords(feat)
    in_box       = in_bbox(lon, lat)
    if not in_box:
        all_in_bbox = False
    flag = "" if in_box else "  *** OUTSIDE BBOX ***"
    print(f"  {display_name}{flag}")
    print(f"    Coordinates : [{lon:.6f}, {lat:.6f}]")
    print(f"    fire_damage : {p.get('fire_damage')}")
    print()

print(f"All coordinates within bounding box: {'YES' if all_in_bbox else 'NO - see warnings above'}")
print()

if bbox_rejected:
    print(f"-- Rejected by bounding box: {len(bbox_rejected)} school(s) " + "-" * 20)
    for name, lon, lat in bbox_rejected:
        lat_s = f"{lat:.4f}" if lat is not None else "None"
        lon_s = f"{lon:.4f}" if lon is not None else "None"
        print(f"  {name}  [{lon_s}, {lat_s}]")
    print()

if not_found:
    print(f"-- Search terms with no match: {len(not_found)} " + "-" * 30)
    for t in not_found:
        print(f"  - {t}")
    print()
else:
    print("-- All search terms matched. " + "-" * 40)
