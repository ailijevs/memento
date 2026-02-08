# Defect Issue Content for GitHub

**Create this as a new GitHub issue using the Bug Report template.**  
Go to: https://github.com/ailijevs/memento-1/issues/new?template=bug_report.md

---

## Title

`[BUG] Application startup fails when .env contains undefined variables`

---

## Body (fill into template)

### Defect Name

Application startup fails with "Extra inputs are not permitted" when `.env` contains environment variables not defined in `app.config.Settings`.

### Severity

- [ ] High
- [x] Medium
- [ ] Low

### Steps to Reproduce

1. Add an environment variable to `backend/.env` that is not defined in `app.config.Settings` (e.g. `SUPABASE_REDIRECT_URL` or any typo).
2. Start the backend: `uvicorn app.main:app --reload`
3. Observe startup failure.

### Expected Behavior

The application should either:
- Load only known variables and ignore unknown ones, or
- Fail with a clearer error message pointing to the problematic variable.

### Actual Behavior

Pydantic raises `ValidationError: 1 validation error for Settings / extra` with "Extra inputs are not permitted" and the application does not start.

### Test Case ID

MT-01 (manual setup verification) / local environment setup

### Environment

- OS: macOS / Linux / Windows
- Python: 3.11+
- Backend: Memento API v1.0.0

### Logs / Evidence

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
extra
  Extra inputs are not permitted [type=extra_forbidden]
```

---

## Root Cause Analysis (RCA)

*Add this section to the issue after creating it (or paste into the RCA section of the template if you extend it):*

- **How was the defect discovered?** During local setup when a teammate added an env var to `.env` (e.g. for a new feature or from copying another project) that was not yet defined in `Settings`. The app failed to start with an opaque Pydantic error.
- **Which test exposed the issue?** Manual environment setup and MT-01 (health check). No automated test previously validated config loading.
- **How was the fix verified?** Updated `Settings` in `app/config.py` to include the missing variable (or removed the extra var from `.env`). Verified app starts successfully. Documented in CLAUDE.md troubleshooting.
- **What regression test prevents recurrence?** Consider adding a test that loads `Settings` with minimal required vars only. CI already runs with mock env vars, so this catches most config issues.
- **Are there other portions of the codebase where this issue may still occur?** Any new env var used elsewhere (e.g. in scripts) must be added to `Settings` if loaded via `get_settings()`, or documented in `.env.example`.
