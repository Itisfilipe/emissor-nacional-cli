# emissor-nacional-cli

CLI for issuing Brazilian NFS-e (electronic service invoices) via the national system (SEFIN/ADN APIs). Focused on service export invoices for international clients.

## Commands

```bash
uv run pytest tests/ -v --cov # Run tests
uv run ruff check src/ tests/  # Lint
uv run ruff format src/ tests/ # Format
uv run pyright src/             # Type check
```

## Architecture

```
config/                    # YAML config (emitter + clients), gitignored; .example files committed
src/emissor/
  config.py                # Loads YAML config, .env, endpoints
  cli.py                   # Click CLI (emit, validate, query, pdf)
  models/                  # Dataclasses: Emitter, Client, Intermediary, Invoice
  services/
    dps_builder.py         # Builds DPS XML element from models
    xml_signer.py          # Signs XML with ICP-Brasil A1 certificate
    xml_encoder.py         # Encodes signed XML for SEFIN API
    sefin_client.py        # SEFIN API client (submit DPS)
    adn_client.py          # ADN API client (query NFS-e, download DANFSE)
    emission.py            # Orchestrates: config → build → sign → submit
  utils/
    dps_id.py              # Generates 45-char DPS ID
    sequence.py            # Auto-incrementing nDPS sequence (data/sequence.json)
    certificate.py         # Certificate validation
tests/                     # pytest tests
```

## Key concepts

- **DPS** (Declaração de Prestação de Serviços): XML document submitted to SEFIN to generate an NFS-e
- **SEFIN**: Government API that receives DPS and returns NFS-e
- **ADN**: Government API for querying/downloading issued NFS-e
- Config files are YAML; real ones are gitignored, `.example` files are committed
- `EMISSOR_CONFIG_DIR` / `EMISSOR_DATA_DIR` env vars override default path resolution

## TUI design rules

- **Buttons must always have an icon** prefix to distinguish them from other text elements. Use Unicode symbols: `←` (back), `▶` (action/go), `⇓` (download), `↑` (send/upload), `⎘` (copy), `▷` (filter), `⇄` (toggle)
