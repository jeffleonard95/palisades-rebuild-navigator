import json

print("Loading files...")
with open('DINS_2025_Palisades_Public_View.geojson', 'r') as f:
    dins = json.load(f)
with open('parcels.geojson', 'r') as f:
    parcels = json.load(f)

print(f"DINS records: {len(dins['features'])}")
print(f"Parcel records: {len(parcels['features'])}")

def point_in_polygon(point, polygon_coords):
    """Ray casting algorithm for point in polygon"""
    x, y = point
    inside = False
    coords = polygon_coords[0]  # outer ring
    n = len(coords)
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def get_parcel_bbox(polygon_coords):
    """Get bounding box for quick pre-filter"""
    coords = polygon_coords[0]
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lngs), min(lats), max(lngs), max(lats)

print("\nBuilding parcel index...")
parcel_index = []
for feature in parcels['features']:
    props = feature['properties']
    geom = feature['geometry']
    apn = props.get('APN', '')
    address = props.get('SitusAddress', '')
    use_type = props.get('UseType', '')

    if not apn:
        continue

    # Handle both Polygon and MultiPolygon
    if geom['type'] == 'Polygon':
        polygons = [geom['coordinates']]
    elif geom['type'] == 'MultiPolygon':
        polygons = geom['coordinates']
    else:
        continue

    for poly_coords in polygons:
        bbox = get_parcel_bbox(poly_coords)
        parcel_index.append({
            'apn': apn,
            'address': address,
            'use_type': use_type,
            'coords': poly_coords,
            'bbox': bbox
        })

print(f"Parcel index built: {len(parcel_index)} polygons")

print("\nJoining DINS points to parcels...")
matched = {}
unmatched = 0
multiple = 0

for i, dins_feature in enumerate(dins['features']):
    if i % 1000 == 0:
        print(f"  Processing {i}/{len(dins['features'])}...")

    props = dins_feature['properties']
    coords = dins_feature['geometry']['coordinates']
    lng, lat = coords[0], coords[1]
    damage = props['DAMAGE']
    struct_type = props['STRUCTURETYPE']

    found_apn = None

    # Check each parcel polygon
    for parcel in parcel_index:
        min_lng, min_lat, max_lng, max_lat = parcel['bbox']

        # Quick bounding box pre-filter
        if not (min_lng <= lng <= max_lng and
                min_lat <= lat <= max_lat):
            continue

        # Full point in polygon check
        if point_in_polygon([lng, lat], parcel['coords']):
            found_apn = parcel['apn']
            break

    if found_apn:
        if found_apn in matched:
            # Multiple structures on same parcel - keep worst damage
            existing = matched[found_apn]['damage']
            damage_rank = {
                'Destroyed (>50%)': 5,
                'Major (26-50%)': 4,
                'Minor (10-25%)': 3,
                'Affected (1-9%)': 2,
                'No Damage': 1
            }
            if damage_rank.get(damage, 0) > damage_rank.get(existing, 0):
                matched[found_apn]['damage'] = damage
            matched[found_apn]['structure_count'] += 1
            multiple += 1
        else:
            matched[found_apn] = {
                'apn': found_apn,
                'damage': damage,
                'structure_type': struct_type,
                'structure_count': 1
            }
    else:
        unmatched += 1

print(f"\nJoin complete:")
print(f"  Matched: {len(matched)} parcels")
print(f"  Unmatched DINS points: {unmatched}")
print(f"  Multiple structures on same parcel: {multiple}")

# Damage breakdown of matched parcels
print("\nDamage breakdown (matched parcels):")
damage_counts = {}
for apn, data in matched.items():
    d = data['damage']
    damage_counts[d] = damage_counts.get(d, 0) + 1
for k, v in sorted(damage_counts.items()):
    print(f"  {v:5d}  {k}")

# Write output
print("\nWriting dins_data.js...")
output = {
    "type": "dins_lookup",
    "total_matched": len(matched),
    "parcels": matched
}

js_content = f"var DINS_DATA = {json.dumps(output, indent=2)};"

with open('dins_data.js', 'w') as f:
    f.write(js_content)

print(f"Done. dins_data.js written with {len(matched)} matched parcels.")
print("\nSample matches:")
for apn, data in list(matched.items())[:5]:
    print(f"  APN {apn}: {data['damage']} — {data['structure_type']}")
