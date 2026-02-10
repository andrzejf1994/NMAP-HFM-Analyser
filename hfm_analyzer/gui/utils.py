"""Utility helpers and shared constants for the GUI package."""

from __future__ import annotations

import os
import re
import string

from PyQt5.QtWidgets import QInputDialog, QMessageBox, QWidget

from hfm_analyzer.data_labels import (
    GRIP_PARAM_FIELDS,
    GRIP_PARAM_ORDER,
    HAIRPIN_PARAM_FIELDS,
    HAIRPIN_PARAM_LABELS,
    HAIRPIN_PARAM_ORDER,
    NEST_PARAM_FIELDS,
    NEST_PARAM_ORDER,
)

from hfm_analyzer.utils import (
    extract_unc_share,
    list_mapped_network_drives,
    map_network_drive,
    map_unc_to_drive_if_possible,
)


TRACKED_MACHINE_CODES: set[str] = {f"M{i}" for i in range(1, 7)} | {f"S{i}" for i in range(1, 7)}


HAIRPIN_PARAM_EXCLUDE: set[str] = {
    "r64LunghezzaStripTaglioIniziale",
    "r64LunghezzaStripTaglioFinale",
}


def _available_drive_letters() -> list[str]:
    """Return available drive letters for mapping network shares on Windows."""

    if os.name != "nt":
        return []

    used_letters: set[str] = set()
    try:
        for _, drive, _ in list_mapped_network_drives():
            used_letters.add(drive.rstrip(":").upper())
    except Exception:
        pass

    for letter in string.ascii_uppercase:
        if letter < "D":
            continue
        try:
            if os.path.exists(f"{letter}:\\"):
                used_letters.add(letter)
        except Exception:
            continue

    return [
        letter
        for letter in string.ascii_uppercase
        if "D" <= letter <= "Z" and letter not in used_letters
    ]


def _maybe_offer_drive_mapping(parent: QWidget, path: str, *, fast: bool = False) -> str:
    """Offer mapping for a UNC path when no matching mapped drive exists."""

    if not path:
        return path
    normalized_original = path.replace("/", "\\")
    if not normalized_original.startswith("\\\\"):
        return path

    try:
        mapped = path if fast else map_unc_to_drive_if_possible(path)
    except Exception:
        mapped = path

    normalized_mapped = mapped.replace("/", "\\")

    if normalized_mapped != normalized_original:
        return mapped

    share = extract_unc_share(path)
    if not share or os.name != "nt":
        return mapped

    answer = QMessageBox.question(
        parent,
        "Mapowanie dysku",
        (
            "Wybrana ścieżka sieciowa nie jest aktualnie zmapowana na literę dysku.\n"
            "Czy chcesz zmapować udział {share}?"
        ).format(share=share),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if answer != QMessageBox.Yes:
        return mapped

    available = _available_drive_letters()
    if not available:
        QMessageBox.warning(
            parent,
            "Brak wolnych liter",
            "Brak wolnych liter dysków do mapowania. Zwolnij literę i spróbuj ponownie.",
        )
        return mapped

    options = [f"{letter}:" for letter in available]
    letter, ok = QInputDialog.getItem(
        parent,
        "Wybierz literę",
        "Wybierz literę dysku dla udziału sieciowego:",
        options,
        0,
        False,
    )
    if not ok or not letter:
        return mapped

    if map_network_drive(share, letter):
        QMessageBox.information(
            parent,
            "Sukces",
            f"Udział {share} został zmapowany jako {letter}.",
        )
        return map_unc_to_drive_if_possible(path)

    QMessageBox.critical(
        parent,
        "Błąd",
        "Nie udało się zmapować dysku. Sprawdź uprawnienia lub spróbuj ponownie.",
    )
    return mapped


def _natural_sort_key(value: str) -> tuple:
    """Return a key for natural sorting of mixed text/numeric strings."""

    if not isinstance(value, str):
        value = str(value)
    parts = re.split(r"(\d+)", value)
    key: list[tuple[int, object]] = []
    for part in parts:
        if part == "":
            continue
        if part.isdigit():
            try:
                key.append((0, int(part)))
            except Exception:
                key.append((0, part))
        else:
            key.append((1, part.lower()))
    return tuple(key)


__all__ = [
    "TRACKED_MACHINE_CODES",
    "GRIP_PARAM_FIELDS",
    "GRIP_PARAM_ORDER",
    "NEST_PARAM_FIELDS",
    "NEST_PARAM_ORDER",
    "HAIRPIN_PARAM_FIELDS",
    "HAIRPIN_PARAM_LABELS",
    "HAIRPIN_PARAM_ORDER",
    "HAIRPIN_PARAM_EXCLUDE",
    "_available_drive_letters",
    "_maybe_offer_drive_mapping",
    "_natural_sort_key",
]
