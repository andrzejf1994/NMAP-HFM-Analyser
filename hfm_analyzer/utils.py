"""Miscellaneous helper utilities used across modules."""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Iterable, List, Tuple


def _split_unc(entry: str) -> List[str]:
    replaced = entry.replace("/", "\\")
    while replaced.startswith("\\"):
        replaced = replaced[1:]
    parts = [part for part in replaced.split("\\") if part]
    return parts


def _core_unc(entry: str) -> str:
    parts = _split_unc(entry)
    if len(parts) >= 2:
        return (parts[0] + "\\" + parts[1]).lower()
    return parts[0].lower() if parts else ""


def _core_and_rest(entry: str) -> tuple[str, str]:
    parts = _split_unc(entry)
    if len(parts) >= 2:
        core = (parts[0] + "\\" + parts[1]).lower()
        rest = "\\".join(parts[2:])
        return core, rest
    if parts:
        return parts[0].lower(), ""
    return "", ""


def extract_unc_share(entry: str) -> str:
    """Return ``\\\\host\\share`` for a UNC path or an empty string when invalid."""

    parts = _split_unc(entry)
    if len(parts) >= 2:
        return f"\\\\{parts[0]}\\{parts[1]}"
    return ""


def list_mapped_network_drives() -> List[Tuple[str, str, str]]:
    """Return list of ``(unc_prefix, drive_letter, raw_unc)`` for mapped network drives."""

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


def map_network_drive(unc_path: str, drive_letter: str, persistent: bool = True) -> bool:
    """Map ``unc_path`` to ``drive_letter`` using ``net use`` on Windows."""

    if not unc_path or not drive_letter:
        return False
    if os.name != "nt":
        return False
    try:
        import subprocess

        letter = drive_letter.rstrip(":").upper()
        cmd = f'net use {letter}: "{unc_path}"'
        if persistent:
            cmd += " /persistent:yes"
        subprocess.check_call(cmd, shell=True)
        return True
    except Exception:
        return False


def network_path_available(path: str) -> bool:
    """Return ``True`` when ``path`` exists and is accessible on disk."""

    if not path:
        return False
    try:
        return os.path.exists(path)
    except Exception:
        return False


def sqlite_cache_available(path: str) -> bool:
    """Return ``True`` when ``path`` exists and can be opened read-only as SQLite."""

    if not path:
        return False
    try:
        if not os.path.exists(path):
            return False
    except Exception:
        return False
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.close()
        return True
    except Exception:
        return False


__all__ = [
    "extract_unc_share",
    "list_mapped_network_drives",
    "map_unc_to_drive_if_possible",
    "map_network_drive",
    "network_path_available",
    "sqlite_cache_available",
]
