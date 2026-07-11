def build_location_context(req):
    return {
        "location_context_id": f"loc_{req.tenant_id}",
        "lat": req.latitude,
        "lon": req.longitude,
        "precision_meters": req.precision_meters,
        "location_known": req.latitude is not None and req.longitude is not None,
        "personal_location_language_allowed": req.precision_meters <= 100,
    }
