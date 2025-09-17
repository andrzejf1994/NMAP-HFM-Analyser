"""Miscellaneous helper utilities used across modules."""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Tuple


def list_mapped_network_drives() -> List[Tuple[str, str]]:
    """Return list of ``(unc_prefix, drive_letter)`` for mapped network drives."""

    mappings: List[Tuple[str, str]] = []

    try:
        import wmi

        c = wmi.WMI()
        for drv in c.Win32_LogicalDisk(DriveType=4):
            unc = (drv.ProviderName or "").rstrip("\\/")
            letter = (drv.DeviceID or "").strip()
            if unc and letter:
                mappings.append((unc, letter))
    except Exception:
        pass

    if not mappings:
        try:
            import subprocess

            out = subprocess.check_output(
                "net use",
                shell=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            for line in out.splitlines():
                match = re.search(r"([A-Z]:)\s+\\\\[^\s]+", line)
                if not match:
                    continue
                drive = match.group(1)
                unc_match = re.search(r"(\\\\[^\s]+)", line)
                if unc_match:
                    unc = unc_match.group(1).rstrip("\\/")
                    mappings.append((unc, drive))
        except Exception:
            pass

    def _normalized(mapping: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
        def _split_unc(entry: str) -> List[str]:
            replaced = entry.replace("/", "\\")
            parts = [part for part in replaced.split("\\") if part]
            return parts

        def _core_unc(entry: str) -> str:
            parts = _split_unc(entry)
            if len(parts) >= 2:
                return (parts[0] + "\\" + parts[1]).lower()
            return (parts[0].lower() if parts else "")

        normalised = [(_core_unc(unc), drv.upper()) for unc, drv in mapping]
        normalised.sort(key=lambda item: len(item[0]), reverse=True)
        return normalised

    return _normalized(mappings)


def map_unc_to_drive_if_possible(path: str) -> str:
    """Replace a UNC prefix with its mapped drive letter when possible."""

    if not path:
        return path

    try:
        def _split_unc(entry: str) -> List[str]:
            replaced = entry.replace("/", "\\")
            while replaced.startswith("\\"):
                replaced = replaced[1:]
            parts = [part for part in replaced.split("\\") if part]
            return parts

        def _core_unc(entry: str) -> tuple[str, str]:
            parts = _split_unc(entry)
            if len(parts) >= 2:
                core = (parts[0] + "\\" + parts[1]).lower()
                rest = "\\".join(parts[2:])
                return core, rest
            if parts:
                return parts[0].lower(), ""
            return "", ""

        core, rest = _core_unc(path)
        if not core:
            return path
        for unc_core, drive in list_mapped_network_drives():
            if core == unc_core:
                remainder = rest.lstrip("\\/")
                return drive + ("\\" + remainder if remainder else "")
    except Exception:
        pass
    return path


def network_path_available(path: str) -> bool:
    """Return ``True`` when ``path`` exists and is accessible on disk."""

    if not path:
        return False
    try:
        return os.path.exists(path)
    except Exception:
        return False


__all__ = [
    "list_mapped_network_drives",
    "map_unc_to_drive_if_possible",
    "network_path_available",
]
