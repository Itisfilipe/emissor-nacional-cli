# emissor-py

CLI para emissão automatizada de NFS-e (Nota Fiscal de Serviço Eletrônica) via o sistema nacional da Receita Federal do Brasil. Voltado para prestadores de serviço que emitem notas para clientes no exterior (exportação de serviços).

## Pré-requisitos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Certificado digital ICP-Brasil tipo A1 (arquivo `.pfx` ou `.p12`)
- Cadastro no portal nacional de NFS-e

## Instalação

```bash
uv sync
```

## Configuração

1. Copie os arquivos de exemplo e preencha com seus dados reais:

```bash
cp config/emitter.yaml.example config/emitter.yaml
cp config/clients/acme-corp.yaml.example config/clients/seu-cliente.yaml
```

2. Crie um arquivo `.env` na raiz do projeto:

```env
CERT_PFX_PATH=/caminho/para/certificado.pfx
CERT_PFX_PASSWORD=sua-senha
```

Se instalar o pacote fora do repositório (ex: via `pip install`), defina também:

```env
EMISSOR_CONFIG_DIR=/caminho/para/config
EMISSOR_DATA_DIR=/caminho/para/data
```

## Uso

```bash
# Validar certificado e configuração
uv run emissor validate

# Emitir NFS-e
uv run emissor emit seu-cliente \
    --valor-brl 19684.93 \
    --valor-usd 3640.00 \
    --competencia 2025-12-30

# Emitir com intermediário
uv run emissor emit seu-cliente \
    --valor-brl 53526.58 \
    --valor-usd 10221.04 \
    --competencia 2025-12-23 \
    --intermediario intermediary

# Dry run (gera XML sem enviar)
uv run emissor emit seu-cliente \
    --valor-brl 19684.93 \
    --valor-usd 3640.00 \
    --competencia 2025-12-30 \
    --dry-run

# Consultar NFS-e pela chave de acesso
uv run emissor query <chave-de-acesso>

# Baixar DANFSE em PDF
uv run emissor pdf <chave-de-acesso> -o nota.pdf

# Usar ambiente de produção (padrão: homologação)
uv run emissor --env producao emit ...
```

## Desenvolvimento

```bash
# Lint
uv run ruff check src/ tests/

# Formatar
uv run ruff format src/ tests/

# Type check
uv run pyright src/

# Testes
uv run pytest tests/ -v
```

## Licença

[MIT](LICENSE)
