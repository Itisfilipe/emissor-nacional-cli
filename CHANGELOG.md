# Registro de mudanças

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/),
e este projeto adota [Versionamento Semântico](https://semver.org/).

## [Unreleased]

### Adicionado

- Validação de CEP no formulário de clientes
- Coluna de erro na tabela do dashboard
- URL do endpoint em mensagens de erro de conectividade
- Verificação de conectividade SEFIN na tela de validação
- Backup automático e verificação de integridade do registro local
- Aviso de saúde do registro no dashboard e tela de validação
- Camada HTTP resiliente com retry/backoff para SEFIN e ADN
- Validadores de campos fiscais no formulário de nova NFS-e
- Validação de chave de acesso nas telas de consulta e download
- Ciclo de vida draft/promote/fail no registro de notas
- Novos status e filtros no dashboard
- Campos de override no modelo Invoice e builder DPS
- Campos Select para campos enumerados (COMEX, etc.)

### Corrigido

- Normalização de valor percentual no formulário de nova NFS-e
- Propagação de falhas de persistência de rascunho
- Validação estrita de resposta SEFIN para cStat e nNFSe ausentes

## [0.1.0] - 2025-01-01

### Adicionado

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
- Suíte de testes automatizados

[Unreleased]: https://github.com/Itisfilipe/emissor-nacional-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Itisfilipe/emissor-nacional-cli/releases/tag/v0.1.0
