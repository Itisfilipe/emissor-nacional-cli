# Roadmap

> TUI/CLI para emissão de NFS-e (Nota Fiscal de Serviços Eletrônica) via o sistema nacional (SEFIN/ADN).

A base de segurança para produção está completa — validação de contrato de resposta, validação de campos fiscais, resiliência HTTP, integridade do registro local e verificação prévia da SEFIN. Este roadmap acompanha o que vem a seguir.

## Próximos passos

- [ ] **Teste de auto-preenchimento na TUI** — adicionar teste de integração cobrindo o fluxo completo de preenchimento no `NewInvoiceScreen` (selecionar cliente → campos populados do último histórico de NFS-e), incluindo o caso sem histórico.

- [ ] **Separação cliente/intermediário** — intermediários atualmente compartilham o pool de `clients/`, então o seletor de intermediários exibe todas as entradas. Adicionar um campo `kind` nos YAMLs de clientes para que os seletores filtrem corretamente. Incluir caminho de migração para configurações existentes.

## Planejado

- [ ] **Subcomandos CLI não interativos** — adicionar comandos `emit`, `sync`, `query`, `download-pdf`, `validate` e `list` com modo de saída `--json`, permitindo uso em scripts e CI sem a TUI.

- [ ] **Ciclo de vida de notas** — pesquisar suporte da API SEFIN/ADN para operações de cancelamento/substituição (varia por município), depois implementar os fluxos suportados com rastreamento de status no registro local.

- [ ] **Segurança de certificado (fase 2)** — provedores de segredos adicionais (1Password CLI, Vault) como alternativas. Diagnósticos estendidos de certificado (cadeia de confiança, verificação de revogação).

## Futuro

- [ ] **Perfis multi-emitente** — suportar múltiplos YAMLs de emitente com alternância na UI/CLI e sequência/registro isolados por emitente. Apenas se houver necessidade concreta de múltiplos CNPJs.

- [ ] **UX e observabilidade de sincronização** — indicadores de progresso durante sync, resumo pós-sync (contadores de criado/atualizado/ignorado/erro), widget de último sync no dashboard.

- [ ] **Relatórios e exportação** — exportação CSV/JSON das linhas filtradas da tabela de notas, resumos mensais básicos por status/cliente/valor.

- [ ] **Documentação e onboarding** — checklist de prontidão para produção, matriz de troubleshooting para erros comuns de SEFIN/ADN/certificado, notas de decisão arquitetural.

- [ ] **Suporte a NFS-e doméstica** — atualmente o emissor é voltado para exportação de serviços (clientes internacionais, `comExt`, NIF, moeda estrangeira). Para suportar NFS-e doméstica: adicionar seletor de tipo de nota (`exportação` / `doméstica`); ramificar o DPS builder para gerar `comNac` + `endNac` com códigos IBGE em vez de `comExt` + `endExt`; aceitar CPF/CNPJ além de NIF no modelo de cliente; ocultar campos COMEX na TUI quando doméstica; adicionar validadores de CPF/CNPJ; criar exemplos de config para clientes nacionais.

- [ ] **Gestão de crescimento do registro** — estratégia de rotação/arquivamento do registro de notas para que o arquivo ativo se mantenha limitado ao longo dos anos, com dados arquivados ainda consultáveis.
