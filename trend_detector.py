def uncertainty_label(epistemology):
    if epistemology.get("knowledge_state") == "sufficient":
        return "bounded"
    if epistemology.get("knowledge_state") == "partial":
        return "partially_bounded"
    return "unbounded"
