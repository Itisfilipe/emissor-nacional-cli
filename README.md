# emissor-nacional

[![PyPI](https://img.shields.io/pypi/v/emissor-nacional)](https://pypi.org/project/emissor-nacional/)
[![Python](https://img.shields.io/pypi/pyversions/emissor-nacional)](https://pypi.org/project/emissor-nacional/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ferramenta TUI para emissão de NFS-e (Nota Fiscal de Serviço Eletrônica) via o Sistema Nacional da NFS-e (SEFIN/ADN). Voltada para prestadores de serviço que emitem notas para clientes no exterior (exportação de serviços).

## Aviso importante

- Este projeto foi criado para **uso pessoal**.
- Surgiu da necessidade de um fluxo mais prático para emissão, diante da obrigatoriedade de uso do emissor nacional oficial, que na prática pode ser burocrático e pouco produtivo para alguns cenários.
- Este software é **independente e não oficial**: não possui vínculo com a Receita Federal, com a SEFIN, com a ADN nem com qualquer órgão governamental.
- O uso é por conta e risco do usuário.

## Funcionalidades

- Emissão de NFS-e com assinatura digital ICP-Brasil A1
- Consulta de NFS-e emitidas e recebidas via ADN (DFe)
- Download de DANFSE (PDF) por chave de acesso
- Sincronização automática com o servidor ADN
- Validação de certificado digital e configuração
- Suporte a ambientes de homologação e produção
- Interface TUI interativa com navegação por teclado

## Pré-requisitos

- Python 3.11+
- Certificado digital ICP-Brasil tipo A1 (`.pfx` ou `.p12`)
- Cadastro no [portal nacional de NFS-e](https://www.nfse.gov.br/)

## Instalação

### Via `pip` / `pipx`

```bash
pip install emissor-nacional
# ou
pipx install emissor-nacional

# Cria os arquivos de configuração de exemplo
emissor-nacional init
```

### Via fonte (desenvolvimento)

```bash
git clone https://github.com/filipeamaral/emissor-nacional-cli.git
cd emissor-nacional-cli
uv sync
```

## Configuração

### 1. Certificado digital

Crie um arquivo `.env` na raiz do projeto (ou defina as variáveis de ambiente):

```env
CERT_PFX_PATH=/caminho/para/certificado.pfx
CERT_PFX_PASSWORD=sua-senha
```

### 2. Dados do emitente

```bash
cp config/emitter.yaml.example config/emitter.yaml
```

Edite `config/emitter.yaml` com os dados reais do prestador:

```yaml
cnpj: "12345678000199"
razao_social: "SUA EMPRESA LTDA"
logradouro: "RUA EXEMPLO"
numero: "100"
bairro: "CENTRO"
cod_municipio: "4205407"  # código IBGE
uf: "SC"
cep: "88000000"
fone: "48999999999"
email: "contato@suaempresa.com.br"
op_simp_nac: "1"      # 1 = optante Simples Nacional
reg_esp_trib: "0"     # regime especial de tributação
serie: "900"           # série da NFS-e
ver_aplic: "emissor-nacional_0.1.0"
servico:
  cTribNac: "010101"                          # código de tributação nacional
  xDescServ: "Desenvolvimento de Software"    # descrição do serviço
  cNBS: "115022000"                           # código NBS
  tpMoeda: "220"                              # moeda (220 = USD)
  cPaisResult: "US"                           # país do resultado
```

### 3. Clientes

```bash
cp config/clients/acme-corp.yaml.example config/clients/meu-cliente.yaml
```

Edite com os dados do tomador de serviço:

```yaml
nif: "123456789"           # identificação fiscal do cliente (NIF)
nome: "Acme Corp"
pais: "US"
logradouro: "100 Main St"
numero: "100"
bairro: "n/a"
cidade: "New York"
estado: "NY"
cep: "10001"
mec_af_comex_p: "02"      # mecanismo de afastamento do COMEX (prestador)
mec_af_comex_t: "02"      # mecanismo de afastamento do COMEX (tomador)
```

### 4. Diretórios (opcional)

Quando instalado via pip, os diretórios padrão do sistema são usados automaticamente (via `platformdirs`). Para sobrescrever:

```env
EMISSOR_CONFIG_DIR=/caminho/para/config
EMISSOR_DATA_DIR=/caminho/para/data
```

## Uso

```bash
emissor-nacional
```

### Atalhos de teclado

| Tecla   | Ação                                        |
| ------- | ------------------------------------------- |
| `n`     | Nova NFS-e                                  |
| `c`     | Consultar NFS-e                             |
| `p`     | Baixar PDF (DANFSE)                         |
| `y`     | Copiar chave de acesso                      |
| `s`     | Sincronizar com servidor                    |
| `v`     | Validar certificado e configuração          |
| `e`     | Alternar ambiente (homologação / produção)  |
| `j`/`k` | Navegar na tabela (estilo vim)              |
| `f`     | Filtrar por data                            |
| `h`     | Ajuda                                       |
| `q`     | Sair                                        |

### Ambiente padrão

O ambiente padrão é **homologação** (testes). Para emitir notas reais, alterne para produção com `e`.

## Desenvolvimento

```bash
uv run pytest tests/ -v --cov     # testes + cobertura
uv run ruff check src/ tests/     # lint
uv run ruff format src/ tests/    # formatar
uv run pyright src/               # checagem de tipos
```

## Licença

[MIT](LICENSE)
