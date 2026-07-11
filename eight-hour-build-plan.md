{
  "policy_pack_id": "microclimate-confidence-policy-v1",
  "version": "1.0.0",
  "domain": "weather",
  "rules": [
    {
      "rule_id": "MICROCLIMATE_OVERCLAIM_BLOCK",
      "deontic": "MUST_NOT",
      "condition": "microclimate_confidence == low AND claim_type == exact_microclimate_adjusted_forecast",
      "effect_if_failed": "BLOCK",
      "reason_code": "microclimate_overclaim",
      "artifact_required": true
    },
    {
      "rule_id": "LOW_CONFIDENCE_CAUTION",
      "deontic": "SHOULD",
      "condition": "microclimate_confidence != low",
      "effect_if_failed": "PERMIT_WITH_CAUTION",
      "reason_code": "low_microclimate_confidence",
      "artifact_required": true
    }
  ]
}
