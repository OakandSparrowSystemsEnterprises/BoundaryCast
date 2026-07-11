def build_microclimate_context(req, location_context):
    known = 0
    fields = [req.surface_exposure, req.shade_exposure, req.elevation_meters, req.wind_exposure, req.nearby_water, req.urban_density]
    known = sum(1 for x in fields if x is not None)
    if known >= 4:
        confidence = "medium"
    elif known >= 2:
        confidence = "low-medium"
    else:
        confidence = "low"
    return {
        "microclimate_context_id": f"mcx_{req.tenant_id}",
        "surface_exposure": req.surface_exposure or "unknown",
        "shade_exposure": req.shade_exposure or "unknown",
        "elevation_meters": req.elevation_meters,
        "wind_exposure": req.wind_exposure or "unknown",
        "nearby_water": req.nearby_water if req.nearby_water is not None else "unknown",
        "urban_density": req.urban_density or "unknown",
        "microclimate_confidence": confidence,
        "reason": "Confidence is based on the number of known microclimate attributes. Unknown values reduce confidence.",
    }
