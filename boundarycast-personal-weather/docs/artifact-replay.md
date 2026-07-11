# Artifact Replay

Every forecast verdict produces a hash-linked artifact.

The artifact binds tenant, location context, evidence, claim, policy pack versions, Gatekeeper-Lite verdict, reason codes, model versions, timestamp, nonce, previous hash, and current hash.

Replay verifies that the artifact chain has not been tampered with and that verdict context is present.
