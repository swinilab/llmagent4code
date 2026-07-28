# ADR 004: Graceful Degradation via middleware flag

**Decision:** Implement a simple global flag and FastAPI middleware that returns ``503`` for non‑essential endpoints when degradation is active.

**Context:** Addresses NFR 2.1 (Graceful Degradation) ensuring core checkout remains available under load.

**Alternatives considered:**
- Kubernetes Horizontal Pod Autoscaling – rejected because it is infrastructure‑level, not application‑level.
- Feature flags service – rejected for added external dependency; a lightweight in‑process flag suffices.

**Consequences:** Degradation logic is coarse‑grained; future work may replace static flag with dynamic load‑based activation.
