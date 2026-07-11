EXACT_LOCATION_MAX_ACCURACY_METERS = 250


def build_location_context(req):
    return {
        "location_context_id": f"loc_{req.tenant_id}",
        "lat": req.latitude,
        "lon": req.longitude,
        "precision_meters": req.precision_meters,
        "location_known": req.latitude is not None and req.longitude is not None,
        # Browser/Wi-Fi positioning often stabilizes just above 100 m. A
        # 250 m ceiling remains hyperlocal while avoiding a brittle cliff at
        # 100/101 m; multi-kilometer fixes still degrade to area scope.
        "personal_location_language_allowed": req.precision_meters <= EXACT_LOCATION_MAX_ACCURACY_METERS,
    }

