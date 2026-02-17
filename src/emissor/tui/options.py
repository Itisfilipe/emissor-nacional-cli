"""Shared Select option constants for NFS-e form fields.

Values sourced from the official NFS-e Nacional specification.
Labels use "code — description" format.
"""

from __future__ import annotations

MD_PRESTACAO_OPTIONS: tuple[tuple[str, str], ...] = (
    ("0 — Desconhecido", "0"),
    ("1 — Transfronteiriço", "1"),
    ("2 — Consumo no Brasil", "2"),
    ("3 — Presença Comercial no Exterior", "3"),
    ("4 — Movimento Temporário de Pessoas Físicas", "4"),
)

VINC_PREST_OPTIONS: tuple[tuple[str, str], ...] = (
    ("0 — Sem vínculo", "0"),
    ("1 — Controlada", "1"),
    ("2 — Controladora", "2"),
    ("3 — Coligada", "3"),
    ("4 — Matriz", "4"),
    ("5 — Filial ou sucursal", "5"),
    ("6 — Outro vínculo", "6"),
    ("9 — Desconhecido", "9"),
)

MEC_AF_COMEX_P_OPTIONS: tuple[tuple[str, str], ...] = (
    ("00 — Desconhecido", "00"),
    ("01 — Nenhum", "01"),
    ("02 — ACC", "02"),
    ("03 — ACE", "03"),
    ("04 — BNDES-Exim Pós-Embarque", "04"),
    ("05 — BNDES-Exim Pré-Embarque", "05"),
    ("06 — FGE", "06"),
    ("07 — PROEX Equalização", "07"),
    ("08 — PROEX Financiamento", "08"),
)

MEC_AF_COMEX_T_OPTIONS: tuple[tuple[str, str], ...] = (
    ("00 — Desconhecido", "00"),
    ("01 — Nenhum", "01"),
    ("02 — Adm. Pública e Org. Internacionais", "02"),
    ("03 — Aluguel e Afretamento", "03"),
    ("04 — Arrendamento Aeronave Transporte", "04"),
    ("05 — Comissão Agentes Exportação", "05"),
    ("06 — Despesas Armazenagem/Carga", "06"),
    ("07 — Eventos FIFA (subsidiária)", "07"),
    ("08 — Eventos FIFA", "08"),
    ("09 — Fretes e Afretamento", "09"),
    ("10 — Material Aeronáutico", "10"),
    ("11 — Promoção Bens no Exterior", "11"),
    ("12 — Promoção Destinos Turísticos", "12"),
    ("13 — Promoção do Brasil", "13"),
    ("14 — Promoção Serviços no Exterior", "14"),
    ("15 — RECINE", "15"),
    ("16 — RECOPA", "16"),
    ("17 — Registro Marcas/Patentes", "17"),
    ("18 — REICOMP", "18"),
    ("19 — REIDI", "19"),
    ("20 — REPENEC", "20"),
    ("21 — REPES", "21"),
    ("22 — RETAERO", "22"),
    ("23 — RETID", "23"),
    ("24 — Royalties e Assistência Técnica", "24"),
    ("25 — Avaliação Conformidade OMC", "25"),
    ("26 — ZPE", "26"),
)

MOV_TEMP_BENS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("0 — Desconhecido", "0"),
    ("1 — Não", "1"),
    ("2 — Vinculada - Declaração Importação", "2"),
    ("3 — Vinculada - Declaração Exportação", "3"),
)

MDIC_OPTIONS: tuple[tuple[str, str], ...] = (
    ("0 — Não enviar", "0"),
    ("1 — Enviar para o MDIC", "1"),
)

TRIB_ISSQN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("1 — Operação tributável", "1"),
    ("2 — Imunidade", "2"),
    ("3 — Exportação de serviço", "3"),
    ("4 — Não Incidência", "4"),
)

TP_RET_ISSQN_OPTIONS: tuple[tuple[str, str], ...] = (
    ("1 — Não Retido", "1"),
    ("2 — Retido pelo Tomador", "2"),
    ("3 — Retido pelo Intermediário", "3"),
)
