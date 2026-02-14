# Contribuindo

Obrigado pelo interesse em contribuir! Este guia explica como participar do projeto.

## Configuração do ambiente

```bash
git clone https://github.com/filipeamaral/emissor-nacional-cli.git
cd emissor-nacional-cli
uv sync --group dev
```

## Fluxo de trabalho

1. Crie um fork do repositório
2. Crie uma branch a partir de `main` (`git checkout -b minha-feature`)
3. Faça suas alterações
4. Rode as verificações locais (veja abaixo)
5. Faça commit e push para seu fork
6. Abra um Pull Request para `main`

## Verificações obrigatórias

Antes de abrir um PR, todas as verificações devem passar:

```bash
uv run ruff check src/ tests/       # lint
uv run ruff format --check src/ tests/  # formatação
uv run pyright src/                  # checagem de tipos
uv run pytest tests/ -v --cov       # testes + cobertura
```

O CI roda essas mesmas verificações automaticamente em Python 3.11, 3.12 e 3.13.

## Convenções

- **Commits**: mensagens concisas em inglês, no imperativo ("Add feature", não "Added feature")
- **Código**: siga o estilo existente; `ruff` e `pyright` cuidam da maioria
- **Testes**: toda funcionalidade nova deve ter testes correspondentes
- **Branches**: nomes descritivos (ex: `fix-sequence-migration`, `add-client-field`)

## Reportando bugs

Abra uma [issue](https://github.com/filipeamaral/emissor-nacional-cli/issues) com:

- Descrição do problema
- Passos para reprodução
- Comportamento esperado vs. observado
- Versão do Python e do emissor-nacional

## Segurança

Para vulnerabilidades de segurança, siga a [política de segurança](SECURITY.md).
Não abra issues públicas para problemas de segurança.
