def evidence_score(epistemology):
    keys = [k for k, v in epistemology.items() if isinstance(v, bool)]
    if not keys:
        return 0.0
    return round(sum(1 for k in keys if epistemology[k]) / len(keys), 3)
