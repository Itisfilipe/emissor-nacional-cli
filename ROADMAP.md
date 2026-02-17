# Roadmap

> TUI/CLI for issuing Brazilian NFS-e (electronic service invoices) via the national system.

The production safety baseline is complete — response contract enforcement, fiscal input validation, HTTP resilience, registry integrity, and SEFIN preflight checks are all shipped. This roadmap tracks what comes next.

## Up next

- [ ] **Auto-prefill TUI test** — add integration test covering the full prefill flow in `NewInvoiceScreen` (select client -> fields populated from last invoice history), including the no-history edge case.

- [ ] **Client/intermediary separation** — intermediaries currently share the `clients/` pool, so the intermediary selector shows all entries. Add a `kind` field to client YAML configs so selectors can filter correctly. Include a migration path for existing setups.

## Planned

- [ ] **Certificate security hardening (phase 1)** — warn on world-readable PFX files in the Validate screen, document env var best practices for certificate passwords.

- [ ] **Non-interactive CLI subcommands** — add `emit`, `sync`, `query`, `download-pdf`, `validate`, and `list` commands with `--json` output mode, enabling scripting and CI integration without the TUI.

- [ ] **Invoice lifecycle actions** — research SEFIN/ADN API support for cancel/substitute operations (varies by municipality), then implement supported workflows with status tracking in the local registry.

- [ ] **Certificate security hardening (phase 2)** — optional secret providers (OS keychain, 1Password CLI, Vault) as alternatives to env vars. Extended cert diagnostics (chain trust, revocation checks).

## Future

- [ ] **Multi-emitter profiles** — support multiple emitter YAML configs with UI/CLI switching and isolated sequence/registry per emitter. Only pursue if there's a concrete multi-CNPJ need.

- [ ] **Sync UX and observability** — progress indicators during sync, post-sync summary (created/updated/skipped/error counts), last-sync widget in dashboard.

- [ ] **Reporting and export** — CSV/JSON export of filtered invoice table rows, basic monthly summaries by status/client/value.

- [ ] **Documentation and onboarding** — production readiness checklist, troubleshooting matrix for common SEFIN/ADN/cert errors, architecture decision notes.

- [ ] **Registry growth management** — rotation/archival strategy for the invoice registry so the active file stays bounded over years of usage while archived data remains queryable.
