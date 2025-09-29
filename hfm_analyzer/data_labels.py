"""Structured label mappings for parsed XML data."""

from __future__ import annotations

from collections import OrderedDict

GRIP_PARAM_FIELDS: OrderedDict[str, str] = OrderedDict(
    [
        ("r64FuoriIngombroPrelievo", "POSITION FOR WAITING PICKING"),
        ("r64QuotaPrelievo", "PICKING POSITION"),
        ("r64PiantaggioInterferenzaImbuto", "INSERTION POSITION 1ST LEG"),
        ("r64QuotaInserimento2ndLeg", "INSERTION POSITION 2ND LEG"),
        ("r64QuotaPiantaggio", "FINAL INSERTION POSITION"),
        ("r64VelocitaDeposito", "INSERTION SPEED"),
    ]
)

NEST_PARAM_FIELDS: OrderedDict[str, str] = OrderedDict(
    [
        ("r64QuotaTraslazioneCestello", "TRANSLATION 1ST LEG"),
        ("r64QuotaTraslCestello2ndLeg", "TRANSLATION 2ND LEG"),
        ("r64QuotaTrasversaleCestello", "TRANSVERSAL 1ST LEG"),
        ("r64QuotaTrasvCestello2ndLeg", "TRANSVERSAL 2ND LEG"),
        ("r64QuotaRegolazioneCestello", "TOOL ADJUSTMENT"),
        ("r64QuotaContenimentoInterno", "INNER CONTAINMENT"),
        ("r64QuotaContenimentoEsterno", "OUTER CONTAINMENT"),
        ("r64QuotaOrizzontaleImbuto", "FUNNEL HORIZONTAL"),
        ("r64QuotaTrasversaleImbuto", "FUNNEL TRANSVERSAL"),
        ("r64QuotaVerticaleSfogliatore", "FUNNEL VERTICAL"),
        ("r64QuotaOrizzontaleInserimento", "COMPACTOR HORIZONTAL"),
        ("r64QuotaTrasversaleInserimento", "COMPACTOR VERTICAL (2ND LEG)"),
        ("r64QuotaCompattatoreVerticale", "COMPACTOR VERTICAL"),
    ]
)

HAIRPIN_PARAM_FIELDS: OrderedDict[str, str] = OrderedDict(
    [
        ("r64GambaIniz", "DŁUGOŚĆ NÓŻKI POCZĄTKOWEJ"),
        ("r64GambaFinale", "DŁUGOŚĆ NÓŻKI KOŃCOWEJ"),
        ("r64OffsetStripFinale", "KONIEC ODIZOLOWANIA"),
        ("r64LunghezzaStripFinale", "OBSZAR ODIZOLOWANIA (KONIEC)"),
        ("r64OffsetStripIniziale", "POCZĄTEK ODIZOLOWANIA"),
        ("r64LunghezzaStripIniziale", "OBSZAR ODIZOLOWANIA (POCZĄTEK)"),
        ("r64LunghezzaHairpin", "DŁUGOŚĆ PINA"),
    ]
)

GRIP_PARAM_ORDER: list[str] = list(GRIP_PARAM_FIELDS.values())
NEST_PARAM_ORDER: list[str] = list(NEST_PARAM_FIELDS.values())
HAIRPIN_PARAM_LABELS: dict[str, str] = dict(HAIRPIN_PARAM_FIELDS)
HAIRPIN_PARAM_ORDER: list[str] = list(HAIRPIN_PARAM_FIELDS.values())

__all__ = [
    "GRIP_PARAM_FIELDS",
    "GRIP_PARAM_ORDER",
    "NEST_PARAM_FIELDS",
    "NEST_PARAM_ORDER",
    "HAIRPIN_PARAM_FIELDS",
    "HAIRPIN_PARAM_LABELS",
    "HAIRPIN_PARAM_ORDER",
]
