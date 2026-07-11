# ADR 003 – Configuration Management

**Decision:** Use Pydantic `BaseSettings` (in `app/config/settings.py`) to load configuration from environment variables and optional `.env` file.

**Context (NFRs addressed):**
- **NFR 2.3 Deferred Binding:** Settings are read on each request via dependency injection, allowing runtime changes without restart.
- **NFR 2.1 Localization of Changes:** Centralised config isolates impact to components that import `settings`.
- **NFR 2.2 Interface Stability:** Changing config does not affect API contracts.

**Alternatives considered:**
1. **Hard‑coded constants** – Rejected because they require code changes/restarts.
2. **ConfigParser with INI files** – Rejected for lack of type safety and runtime reload support.

**Consequences:**
- Developers can override any setting via environment variables.
- Requires careful handling of secret values (not stored in repo).
