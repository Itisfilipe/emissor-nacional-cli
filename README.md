# Emissor Nacional - CLI para emissão de NFS-e via sistema nacional da Receita Federal do Brasil

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

Se instalar o pacote fora do repositório (ex: via `pip install emissor-nacional`), defina também:

```env
EMISSOR_CONFIG_DIR=/caminho/para/config
EMISSOR_DATA_DIR=/caminho/para/data
```

## Uso

```bash
# Iniciar a TUI interativa (padrão: ambiente de homologação)
uv run emissor-nacional
```

A TUI oferece as seguintes funcionalidades via atalhos de teclado:

| Tecla | Ação |
|-------|------|
| `n` | Nova NFS-e |
| `c` | Consultar NFS-e |
| `p` | Baixar PDF (DANFSE) |
| `y` | Copiar chave de acesso |
| `s` | Sincronizar com servidor |
| `v` | Validar certificado e configuração |
| `e` | Alternar ambiente (homologação/produção) |
| `h` | Ajuda |
| `q` | Sair |

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
