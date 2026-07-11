"""Zero-cache location minimization for durable artifacts.

Personal location is used for the live forecast request only. Durable
artifacts never store raw exact real-world coordinates: they carry a
minimized location binding that is sufficient for replay without becoming
a movement log. Synthetic/demo coordinates may be stored as-is because
they do not describe a real person's position.
"""
import hashlib

ROUNDED_DECIMALS = 2  # ~1.1 km cells: coarse enough to not identify a person
GRID_CELL_DEGREES = 0.05

BINDING_TYPES = ["synthetic", "rounded", "grid_hash", "not_stored"]


def rounded_coordinates(lat, lon):
    return {"lat_rounded": round(lat, ROUNDED_DECIMALS), "lon_rounded": round(lon, ROUNDED_DECIMALS)}


def location_grid_hash(lat, lon):
    cell_lat = round(lat / GRID_CELL_DEGREES) * GRID_CELL_DEGREES
    cell_lon = round(lon / GRID_CELL_DEGREES) * GRID_CELL_DEGREES
    cell = f"{cell_lat:.2f},{cell_lon:.2f}"
    return hashlib.sha256(cell.encode("utf-8")).hexdigest()[:16]


def minimize_location(lat, lon, demo_mode):
    if lat is None or lon is None:
        return {"location_binding_type": "not_stored", "location_binding_value": None}
    if demo_mode:
        return {
            "location_binding_type": "synthetic",
            "location_binding_value": {"lat": lat, "lon": lon, "note": "synthetic demo coordinates"},
        }
    return {
        "location_binding_type": "rounded",
        "location_binding_value": {
            **rounded_coordinates(lat, lon),
            "grid_hash": location_grid_hash(lat, lon),
        },
    }
