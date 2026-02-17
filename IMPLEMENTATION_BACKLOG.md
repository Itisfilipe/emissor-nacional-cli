# Emissor Nacional CLI - Implementation Backlog

Last updated: 2026-02-17
Status: Draft for review before execution

## Goal

Turn the current app into a production-hardened emitter for NFS-e export workflows, without breaking the existing TUI-first experience.

## Priority Model

- P0: Must do before broader production usage (risk/compliance/reliability).
- P1: High-impact product and operational improvements after P0.
- P2: Nice-to-have improvements and UX polish.

## Definition of Done (applies to all tickets)

- Behavior covered by automated tests (unit and/or TUI integration).
- README/help text updated when user-facing behavior changes.
- Errors are actionable (clear message + next action).
- No regressions in `uv run pytest tests/ -v --cov`, `uv run ruff check src/ tests/`, `uv run pyright src/`.

## P0 - Critical

### P0-01 - Enforce SEFIN response contract before success UI ✅
Problem:
- Emission can show success even when key fields are missing in API response. `submit()` in `emission.py` returns a result dict regardless of whether `chNFSe` is present — the TUI then displays "N/A" but frames it as a successful emission.

Scope:
- Validate SEFIN response payload in service layer.
- Require presence and validity of `chNFSe`, `nNFSe`, and process status fields before returning success.
- Map SEFIN error payloads to structured domain errors.

Acceptance criteria:
- Emission returns failure if `chNFSe` is absent or blank.
- UI only shows "success" when response contract is valid.
- Tests cover partial success and malformed success payloads.

Dependencies:
- None.

### P0-02 - Harden fiscal input validation ✅
Problem:
- Several fields accept free-form values that should be strongly validated.

Scope:
- First pass: validate fields that directly hit the DPS XML — `cTribNac`, `cNBS`, `tpMoeda` (ISO 4217 numeric), `cPaisResult` (ISO 3166-1 alpha-2), CST PIS/COFINS, access key format.
- Second pass: decimal precision/bounds for percent fields, postal code formats, Query/Download PDF/Clients screens.
- Current `validators.py` only covers dates and monetary values; the module needs extending.

Acceptance criteria:
- Invalid format is blocked before network call.
- Error messages identify field + expected format.
- Validation rules are unit tested with positive and negative cases.

Dependencies:
- None.

Note: Scope is broad — recommended to split into two passes (XML-critical fields first, cosmetic fields second) to avoid blocking other P0 work.

### P0-03 - Add resilient HTTP layer (retry/backoff/timeouts) ✅
Problem:
- API calls use single-attempt requests; transient failures degrade reliability.

Scope:
- Create shared HTTP helper for ADN/SEFIN with retry strategy, bounded exponential backoff, and consistent timeout handling.
- Add per-action retry caps and user-facing error context.

Acceptance criteria:
- Retry behavior is deterministic and configurable.
- Transient failure tests validate retry then success path.
- Non-retryable failures return immediately with clear message.

Dependencies:
- None.

Note: SEFIN submit is **not idempotent** — a retry on ambiguous failure could double-emit a fiscal document. Retries for submit must be limited to connection-level errors (DNS, TCP timeout) where no HTTP response was received. Any HTTP response (including 5xx) should be treated as non-retryable for submit. ADN operations (query, sync, download) are read-only and safe to retry freely.

### ~~P0-04 - Protect local registry/sync state against corruption~~ Done
Problem:
- Malformed JSON is silently reset to `[]` in `registry.py:_load()`, risking hidden loss of the entire invoice history with no user warning.

Scope:
- On parse failure, move corrupted file to timestamped backup.
- Show warning in dashboard/validation with recovery instructions.
- Add optional import/rebuild utility for registry from local XML + ADN sync.

Acceptance criteria:
- Corrupted files are preserved in backup, not discarded.
- User sees explicit warning with backup path.
- Recovery flow is documented and tested.

Dependencies:
- None.

Note: This is a quick win (few hours of work) and should be prioritized ahead of P0-03 in execution order.

### P0-05 - Extend validation screen with SEFIN preflight
Problem:
- Validation checks ADN connectivity, but not SEFIN submit path health.

Scope:
- Add SEFIN connectivity/preflight check in Validate screen.
- Include environment-specific endpoint status in results.
- Distinguish cert/config errors from endpoint/network errors.

Acceptance criteria:
- Validate screen reports ADN and SEFIN independently.
- Failure output includes endpoint and probable cause.
- Tests cover both success and failure branches.

Dependencies:
- P0-03 recommended first (shared HTTP behavior).

### P0-06 - Record failed/draft emissions in registry
Problem:
- `next_n_dps()` increments the sequence atomically in `prepare()`, but if `submit()` fails afterward, the sequence number is burned with no record. This creates audit gaps that are invisible to the user and difficult to explain to fiscal authorities.

Scope:
- Write a "draft" or "prepared" registry entry during `prepare()` (before submission).
- Update the entry to "emitida" on successful `submit()`, or "falha" on failure.
- Dashboard should display these entries with their status so gaps are visible.

Acceptance criteria:
- Every `prepare()` call creates a registry entry.
- Failed submissions are visible in the dashboard with error context.
- Sequence gaps are auditable from the registry alone.

Dependencies:
- None.

## P1 - High Impact

### P1-01 - Add non-interactive CLI subcommands
Problem:
- Operations are mostly TUI-only, limiting automation/CI usage.

Scope:
- Add commands: `emit`, `sync`, `query`, `download-pdf`, `validate`, `list`.
- Support JSON output mode for automation (`--json`).
- Preserve current `emissor-nacional` (TUI) default behavior.

Acceptance criteria:
- Each command can run without TUI.
- Exit codes are reliable for scripting.
- README includes automation examples.

Dependencies:
- P0-01 and P0-02 first.

Note: The current `cli.py` is just an entry point to the TUI — this is essentially a new interface layer. Consider whether there's an active CI/scripting need before prioritizing over other P1 items.

### P1-02 - Implement invoice lifecycle actions (cancel/substitute)
Problem:
- Only issue/query/download/sync are present; no lifecycle event handling.

Scope:
- Research what the national SEFIN/ADN APIs actually expose for cancel/substitute — support varies significantly and many municipalities don't support these operations through the national system yet.
- If supported: add cancel and substitute workflows, persist lifecycle status transitions in local registry, expose actions in dashboard and CLI.

Acceptance criteria:
- API capabilities are documented per environment.
- User can execute and track supported lifecycle events end-to-end.
- Registry status is updated and visible in table/filtering.
- Unsupported operations show clear messaging.

Dependencies:
- P0-01, P0-03, P0-04.

Note: Downgraded from original P1 urgency. Start with an API research spike before scoping implementation — the national system's cancel/substitute support is environment-specific and may not be available.

### P1-03 - Separate client vs intermediary models in config UX
Problem:
- Intermediaries are loaded from the same `clients/` directory and `list_clients()` pool. The intermediary select in the New Invoice screen shows all clients, not just intermediaries.

Scope:
- Introduce explicit config separation (`clients/` and `intermediaries/`) or a required `kind` field in the YAML.
- Update selectors and persistence rules.
- Add migration for existing setups.

Acceptance criteria:
- Intermediary selector only lists intermediary entries.
- Backward-compatible migration path is documented.
- Existing tests updated plus migration coverage.

Dependencies:
- None.

Note: A `kind` field in the YAML is the lightest approach and avoids directory restructuring.

### P1-04 - Multi-emitter profile support
Problem:
- App assumes a single emitter profile.

Scope:
- Support multiple emitter YAML profiles.
- Add UI/CLI mechanism to switch active emitter.
- Isolate sequence/registry by emitter identity and environment.

Acceptance criteria:
- User can switch emitter without manual file edits.
- No sequence collision across emitter profiles.
- Dashboard clearly shows active emitter profile.

Dependencies:
- P0-04 recommended (data safety).

Note: Significant architectural change (sequence isolation, registry partitioning, config resolution). Only pursue if there's a concrete multi-CNPJ need — the blast radius is high relative to ROI for single-emitter users.

### P1-05 - Security hardening for certificate/password handling
Problem:
- Password is env-only and cert validation is basic validity window check.

Scope:
- Phase 1 (quick): Add PFX file permission check in Validate screen, document env var best practices, warn on world-readable cert files.
- Phase 2 (heavy): Add optional secure secret providers (OS keychain, 1Password CLI, Vault) while keeping env fallback. Extend cert checks (chain trust diagnostics, optional revocation/OCSP if feasible).

Acceptance criteria:
- Phase 1: Validation warns on insecure file permissions. Security docs include setup examples.
- Phase 2: User can run without plaintext password in shell history. Validation output clearly distinguishes cert validity vs trust chain issues.

Dependencies:
- None.

Note: Split into two phases. Phase 1 is a quick P1 win. Phase 2 (provider abstraction) is closer to P2 effort.

### P1-06 - TUI integration test for auto-prefill from last invoice
Problem:
- The recently added auto-prefill feature (`on_select_changed` -> `_load_last_overrides` -> `_fill_last_overrides`) has unit tests for the registry layer but no TUI integration test verifying the full flow through the screen.

Scope:
- Add TUI test in `tests/test_tui/test_new_invoice.py` that: creates a registry entry with overrides, mounts `NewInvoiceScreen`, selects the same client, and asserts that Step 2/3 fields are populated from history.
- Cover edge case: first invoice for client (no history, fields unchanged).

Acceptance criteria:
- TUI test exercises the full prefill path end-to-end.
- No-history case is tested as a no-op.

Dependencies:
- None.

## P2 - Enhancement

### P2-01 - Better sync UX and observability
Scope:
- Progress indicator/counters for long sync.
- Optional verbose logs export for support/debug.
- Last sync summary widget in dashboard.

Acceptance criteria:
- User can see progress during sync.
- Post-sync summary shows created/updated/skipped/error counts.

### P2-02 - Reporting and export
Scope:
- CSV/JSON export of filtered table rows.
- Basic monthly summary by status/client/value.

Acceptance criteria:
- Export respects current filters and environment.
- Report output is deterministic and tested.

### P2-03 - Documentation and onboarding upgrades
Scope:
- Add "production readiness checklist".
- Add troubleshooting matrix (SEFIN/ADN/common cert errors).
- Add architecture decision notes for retries, registry integrity, lifecycle model.

Acceptance criteria:
- New user can complete setup using docs only.
- Top operational failure modes have documented runbooks.

### P2-04 - Registry growth management
Problem:
- `_load()` in `registry.py` reads the entire JSON file into memory on every operation. Fine for hundreds of invoices, but will degrade over years of usage.

Scope:
- Add simple rotation/archival strategy (e.g., archive entries older than N months to a separate file).
- Keep archived entries queryable for history lookups.

Acceptance criteria:
- Active registry stays bounded.
- Archived data remains accessible for reporting and `get_last_overrides`.

## Recommended Execution Order

1. ~~P0-01 (response contract — prevents silent fiscal errors)~~ Done
2. ~~P0-04 (registry backup — quick win, protects data before other changes)~~ Done
3. P0-06 (draft entries — complements P0-01, closes audit gaps)
4. ~~P0-02 (input validation — first pass on XML-critical fields)~~ Done
5. ~~P0-03 (HTTP resilience — ADN-only retries first, then SEFIN connection-level)~~ Done
6. P0-05 (SEFIN preflight — builds on P0-03)
7. P1-06 (auto-prefill TUI test — quick, closes testing gap)
8. P1-03 (client/intermediary separation)
9. P1-05 phase 1 (file permission checks)
10. P1-01 (CLI subcommands)
11. P1-02 (lifecycle — after API research spike)
12. P1-04 (multi-emitter — only if needed)
13. P1-05 phase 2 (secret providers)
14. P2 items

## Suggested Milestones

### Milestone A - Production Safety Baseline (P0 complete)
Exit criteria:
- All P0 tickets done and released.

### Milestone B - Operational Capability (P1 partial)
Exit criteria:
- CLI subcommands + lifecycle support shipped.

### Milestone C - Scale and UX (P1/P2 complete)
Exit criteria:
- Multi-emitter + observability + reporting in place.
