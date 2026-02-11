# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2025-01-01

### Added

- TUI interativa com Textual: dashboard, navegação por teclado, filtros por data
- Emissão de NFS-e: construção de DPS XML, assinatura digital ICP-Brasil A1, envio via SEFIN
- Consulta de NFS-e emitidas e recebidas via ADN (DFe) com paginação
- Download de DANFSE (PDF) por chave de acesso
- Sincronização automática com servidor ADN
- Validação de certificado digital e configuração
- Suporte a ambientes de homologação e produção
- Registro local de notas emitidas (`data/invoices.json` com file-lock)
- Sequência automática de nDPS (`data/sequence.json`)
- Configuração via YAML (emitente e clientes) e `.env` (certificado)
- Variáveis de ambiente `EMISSOR_CONFIG_DIR` / `EMISSOR_DATA_DIR` para instalação global
- Suite de testes com 96 testes e 97% de cobertura

[0.1.0]: https://github.com/filipeamaral/emissor-nacional-cli/releases/tag/v0.1.0
