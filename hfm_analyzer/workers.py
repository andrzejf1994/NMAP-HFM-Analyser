"""Background worker threads responsible for I/O bound tasks."""

from __future__ import annotations

import glob
import logging
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QThread, pyqtSignal

from .constants import INDEX_PARAM_NAMES, PARAM_NAMES
from .models import FoundFile, IndexSnapshot, ParamSnapshot

try:  # Optional acceleration when lxml is available.
    import lxml.etree as LET  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    LET = None  # type: ignore


class ScanWorker(QThread):
    """Scan the backup directory tree for XML files in the selected range."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, base_path: str, machines: List[str], start_dt: datetime, end_dt: datetime) -> None:
        super().__init__()
        self.base_path = base_path
        self.machines = machines
        self.start_dt = start_dt.replace(second=0)
        self.end_dt = end_dt.replace(second=0)

    def run(self) -> None:  # pragma: no cover - executed in background thread
        try:
            found: list[FoundFile] = []
            day = self.start_dt.date()
            total_days = (self.end_dt.date() - day).days + 1
            day_idx = 0
            while day <= self.end_dt.date():
                day_idx += 1
                self.progress.emit(f"Skanuję dzień {day_idx}/{total_days}: {day.isoformat()}")
                yyyy = f"{day.year:04d}"
                mm = f"{day.month:02d}"
                yyyy_mm_dd = day.strftime("%Y-%m-%d")
                for machine in self.machines:
                    day_dir = os.path.join(self.base_path, machine, yyyy, mm, yyyy_mm_dd)
                    pattern = os.path.join(day_dir, f"{machine}_{yyyy_mm_dd}_*.xml")
                    for file_path in glob.glob(pattern):
                        try:
                            if not os.path.isfile(file_path):
                                continue
                            parts = os.path.basename(file_path).split("_")
                            if len(parts) < 3:
                                continue
                            dt_str = parts[1] + "_" + parts[2].replace(".xml", "")
                            file_dt = datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S").replace(second=0)
                            if self.start_dt <= file_dt <= self.end_dt:
                                found.append(FoundFile(machine=machine, dt=file_dt, path=file_path))
                        except Exception:
                            continue
                day += timedelta(days=1)
            self.finished.emit(found)
        except Exception as exc:  # pragma: no cover - defensive programming
            self.error.emit(str(exc))


STEP_SPEED_LABEL = "Step Speed"


class AnalyzeWorker(QThread):
    """Parse backup XML files and extract parameter snapshots."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, files: Iterable[FoundFile], max_workers: int | None = None) -> None:
        super().__init__()
        self.files = list(files)
        if max_workers is None:
            try:
                cpu_workers = os.cpu_count() or 4
            except Exception:
                cpu_workers = 4
            max_workers = min(8, max(2, cpu_workers))

        try:
            env_workers = os.environ.get("HFM_ANALYSIS_WORKERS")
            if env_workers:
                value = int(env_workers)
                if value > 0:
                    max_workers = min(32, value)
        except Exception:
            pass
        self.max_workers = max_workers
        logging.getLogger(__name__).info(
            "[AnalyzeWorker] init: files=%s max_workers=%s", len(self.files), self.max_workers
        )

    def run(self) -> None:  # pragma: no cover - executed in background thread
        try:
            param_results: list[ParamSnapshot] = []
            index_results: list[IndexSnapshot] = []
            total = len(self.files)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._analyze_file, file): file for file in self.files}
                done = 0
                for future in as_completed(futures):
                    done += 1
                    found_file = futures[future]
                    self.progress.emit(
                        f"Analizuję plik {done}/{total}: {os.path.basename(found_file.path)}"
                    )
                    try:
                        param_recs, index_recs = future.result()
                        if param_recs:
                            param_results.extend(param_recs)
                        if index_recs:
                            index_results.extend(index_recs)
                    except Exception:
                        logging.getLogger(__name__).exception("[AnalyzeWorker] błąd podczas analizy pliku")
                        continue
            self.finished.emit({'params': param_results, 'index': index_results})
        except Exception as exc:  # pragma: no cover - defensive programming
            self.error.emit(str(exc))

    # The parsing logic is intentionally kept private because it is always executed in worker threads.
    def _analyze_file(self, found_file: FoundFile) -> Tuple[list[ParamSnapshot], list[IndexSnapshot]]:
        param_records: list[ParamSnapshot] = []
        index_records: list[IndexSnapshot] = []
        if LET is not None:
            parser = LET.XMLParser(huge_tree=True, recover=True)  # type: ignore[arg-type]
            root = LET.parse(found_file.path, parser=parser).getroot()  # type: ignore[call-arg]
            iter_items = root.iter
        else:
            root = ET.parse(found_file.path).getroot()
            iter_items = root.iter

        def _parse_float(raw: str | None) -> float | None:
            if raw is None:
                return None
            text = raw.strip().replace(",", ".")
            if not text:
                return None
            try:
                return float(text)
            except Exception:
                return None

        def _parse_bool(raw: str | None) -> bool:
            if raw is None:
                return False
            text = raw.strip().lower()
            if not text:
                return False
            if text in {"1", "true", "tak", "yes", "y"}:
                return True
            if text in {"0", "false", "nie", "no", "n"}:
                return False
            try:
                return bool(int(text))
            except Exception:
                return text not in {"0", "false"}

        def _parse_mode(raw: str | None) -> str:
            if raw is None:
                return "ABS"
            text = raw.strip().lower()
            if not text:
                return "ABS"
            try:
                value = int(text)
            except Exception:
                value = None
            if value is not None:
                return "REL" if value == 1 else "ABS"
            if text in {"rel", "relative", "r"}:
                return "REL"
            if text in {"abs", "absolute", "a"}:
                return "ABS"
            return "REL" if text not in {"0", "false"} else "ABS"

        program = ""
        for item in iter_items("Item"):
            if item.get("name") == "sgFileName":
                program = item.get("value") or ""
                break

        pin_map: dict[str, str] = {}
        a_hair = None
        a_kin = None
        a_index = None
        for array in iter_items("Array"):
            name = array.get("name")
            if name == "aHairPinType" and a_hair is None:
                a_hair = array
            elif name == "aKinTable" and a_kin is None:
                a_kin = array
            elif name == "aIndexTable" and a_index is None:
                a_index = array
            if a_hair is not None and a_kin is not None and a_index is not None:
                break

        if a_hair is not None:
            for struct in a_hair.iter("Struct"):
                idx = struct.get("idx") or ""
                pin = ""
                for item in struct.iter("Item"):
                    if item.get("name") == "sgDescrizione":
                        pin = item.get("value") or ""
                        break
                pin_map[idx] = pin

        if a_kin is not None:
            for struct in a_kin.iter("Struct"):
                struct_idx = struct.get("idx") or ""
                pin_name = pin_map.get(struct_idx, "")

                steps_arr = None
                for array in struct.findall("Array"):
                    if array.get("name") == "Step":
                        steps_arr = array
                        break
                if steps_arr is None:
                    continue

                for step_index, step_el in enumerate(steps_arr.findall("Struct"), start=1):
                    array_map: dict[str, ET.Element] = {}
                    for array in step_el.findall("Array"):
                        name = array.get("name")
                        if not name:
                            continue
                        array_map[name] = array

                    r_pos = array_map.get("rPos")
                    if r_pos is None:
                        continue
                    bo_ax = (
                        array_map.get("boAxIncluded")
                        or array_map.get("boAxisIncluded")
                        or array_map.get("boAxInclude")
                    )
                    bo_mode = (
                        array_map.get("boAxModeRel")
                        or array_map.get("boModeRel")
                        or array_map.get("boMode")
                    )

                    pos_items = list(r_pos.findall("Item"))
                    inc_items = list(bo_ax.findall("Item")) if bo_ax is not None else []
                    mode_items = list(bo_mode.findall("Item")) if bo_mode is not None else []

                    values: dict[str, float | None] = {name: None for name in PARAM_NAMES}
                    included: dict[str, bool] = {name: False for name in PARAM_NAMES}
                    modes: dict[str, str] = {name: "ABS" for name in PARAM_NAMES}

                    for idx, name in enumerate(PARAM_NAMES):
                        if idx < len(pos_items):
                            values[name] = _parse_float(pos_items[idx].get("value"))
                        if idx < len(inc_items):
                            included[name] = _parse_bool(inc_items[idx].get("value"))
                        if idx < len(mode_items):
                            modes[name] = _parse_mode(mode_items[idx].get("value"))

                    step_speed = None
                    speed_arrays = [
                        array_map.get("rStepSpeed"),
                        array_map.get("StepSpeed"),
                        array_map.get("rSpeed"),
                        array_map.get("rVel"),
                    ]
                    for speed_arr in speed_arrays:
                        if speed_arr is None:
                            continue
                        speed_items = list(speed_arr.findall("Item"))
                        if not speed_items:
                            continue
                        step_speed = _parse_float(speed_items[0].get("value"))
                        if step_speed is not None:
                            break
                    if step_speed is None:
                        for item in step_el.findall("Item"):
                            name = item.get("name")
                            if name in {"rStepSpeed", "StepSpeed", "rSpeed"}:
                                step_speed = _parse_float(item.get("value"))
                                break

                    values[STEP_SPEED_LABEL] = step_speed

                    param_records.append(
                        ParamSnapshot(
                            dt=found_file.dt,
                            machine=found_file.machine,
                            program=program,
                            table=struct_idx,
                            pin=pin_name,
                            step=step_index,
                            values=values,
                            included=included,
                            modes=modes,
                            path=found_file.path,
                        )
                    )

        if a_index is not None:
            for struct in a_index.iter("Struct"):
                struct_idx = struct.get("idx") or ""
                steps_arr = None
                for array in struct.findall("Array"):
                    if array.get("name") == "Step":
                        steps_arr = array
                        break
                if steps_arr is None:
                    continue

                for fallback_idx, step_el in enumerate(steps_arr.findall("Struct")):
                    step_idx_attr = step_el.get("idx")
                    try:
                        step_number = int(step_idx_attr) if step_idx_attr is not None else fallback_idx
                    except Exception:
                        step_number = fallback_idx

                    array_map: dict[str, ET.Element] = {}
                    for array in step_el.findall("Array"):
                        name = array.get("name")
                        if not name:
                            continue
                        array_map[name] = array

                    r_pos = array_map.get("rPos")
                    bo_ax = (
                        array_map.get("boAxIncluded")
                        or array_map.get("boAxisIncluded")
                        or array_map.get("boAxInclude")
                    )
                    if r_pos is None or bo_ax is None:
                        continue
                    bo_mode = array_map.get("boModeRel") or array_map.get("boAxModeRel")

                    pos_items = list(r_pos.findall("Item"))
                    inc_items = list(bo_ax.findall("Item"))
                    mode_items = list(bo_mode.findall("Item")) if bo_mode is not None else []

                    values: dict[str, float] = {}
                    included: dict[str, bool] = {}
                    modes: dict[str, str] = {}
                    any_enabled = False

                    for idx, name in enumerate(INDEX_PARAM_NAMES):
                        include = False
                        if idx < len(inc_items):
                            include = _parse_bool(inc_items[idx].get("value"))
                        included[name] = include
                        if include:
                            any_enabled = True

                        parsed_value = (
                            _parse_float(pos_items[idx].get("value")) if idx < len(pos_items) else None
                        )
                        values[name] = parsed_value if parsed_value is not None else 0.0

                        mode = "ABS"
                        if idx < len(mode_items):
                            mode = _parse_mode(mode_items[idx].get("value"))
                        modes[name] = mode

                    if not any_enabled:
                        continue

                    override = None
                    for item in step_el.findall("Item"):
                        if item.get("name") == "iOverride":
                            override = _parse_float(item.get("value"))
                            break

                    index_records.append(
                        IndexSnapshot(
                            dt=found_file.dt,
                            machine=found_file.machine,
                            program=program,
                            table=struct_idx,
                            step=step_number,
                            values=values,
                            included=included,
                            modes=modes,
                            override=override,
                            path=found_file.path,
                        )
                    )

        return param_records, index_records


class IntranetWorker(QThread):
    """Download and parse NOK information from the intranet service."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        url: str,
        start_dt: datetime,
        end_dt: datetime,
        line_id: int,
        excludes: List[str] | None = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.line_id = line_id
        self.excludes = set(excludes or [])

    def run(self) -> None:  # pragma: no cover - executed in background thread
        try:
            data = self._fetch()
            self.finished.emit(data)
        except Exception as exc:  # pragma: no cover - defensive programming
            logging.getLogger(__name__).exception("[IntranetWorker] Błąd pobierania danych")
            self.error.emit(str(exc))

    def _fetch(self) -> dict:
        import urllib.parse
        import urllib.request

        start_date = self.start_dt.strftime("%Y-%m-%d")
        end_date = self.end_dt.strftime("%Y-%m-%d")
        payload = {
            "linia[]": str(self.line_id),
            "data_od": start_date,
            "data_do": end_date,
            "dokument": "view",
        }
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(self.url, data=encoded, method="POST")
        self.progress.emit(f"[Intranet] POST {self.url} payload={payload}")

        html: str | None = None
        try:  # Prefer requests session if available for cookies / redirects support.
            import requests

            with requests.Session() as session:
                response = session.post(self.url, data=payload, timeout=8)
                if response.status_code == 200:
                    html = response.text
                self.progress.emit(
                    f"[Intranet] HTTP status via requests: {getattr(response, 'status_code', '?')}"
                )
        except Exception:
            pass

        if html is None:
            with urllib.request.urlopen(request, timeout=8) as resp:  # type: ignore[arg-type]
                html = resp.read().decode("utf-8", errors="ignore")
                status = getattr(resp, "status", "200 or unknown")
            self.progress.emit(f"[Intranet] HTTP status via urllib: {status}")

        self.progress.emit(f"[Intranet] HTML length: {len(html) if html else 0}")

        rows: list[list[str]] = []
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table")
            if table:
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if len(cells) >= 5:
                        rows.append(cells)
        except Exception:
            for line in (html or "").splitlines():
                if "<tr" not in line or "</tr>" not in line:
                    continue
                cells: list[str] = []
                for match in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", line, re.I):
                    text = re.sub("<[^<]+?>", "", match.group(1))
                    cells.append(text.strip())
                if len(cells) >= 5:
                    rows.append(cells)

        header: list[str] | None = None
        data_rows: list[list[str]] = []
        for row in rows:
            if header is None:
                lowered = [cell.lower() for cell in row]
                if any("serial_no" in cell for cell in lowered) or any(
                    "judge" in cell for cell in lowered
                ) or any("data" in cell for cell in lowered):
                    header = row
                    self.progress.emit(f"[Intranet] Header: {header}")
                    continue
            data_rows.append(row)
        if data_rows:
            self.progress.emit(f"[Intranet] First row: {data_rows[0]}")
        self.progress.emit(f"[Intranet] Parsed rows: {len(data_rows)}")

        if not header:
            return {"per_day": {}, "rows": []}

        def _col_index(name: str) -> int:
            for idx, column in enumerate(header):
                if name.lower() in column.lower():
                    return idx
            return -1

        i_masz_sap = _col_index("maszyna_sap")
        i_masz_opis = _col_index("maszyna_opis")
        i_data = _col_index("data")
        i_serial = _col_index("serial_no")
        i_judge = _col_index("judge")
        self.progress.emit(
            "[Intranet] Col idx: data=%s, serial_no=%s, judge=%s, masz_sap=%s, opis=%s"
            % (i_data, i_serial, i_judge, i_masz_sap, i_masz_opis)
        )

        entries_all: list[dict] = []
        entries_nok: list[dict] = []
        for row in data_rows:
            try:
                dtxt = row[i_data]
                parsed_dt = None
                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%d.%m.%Y %H:%M:%S",
                    "%d.%m.%Y %H:%M",
                ):
                    try:
                        parsed_dt = datetime.strptime(dtxt, fmt)
                        break
                    except Exception:
                        continue
                if parsed_dt is None:
                    continue
                if not (self.start_dt <= parsed_dt <= self.end_dt):
                    continue
                serial = row[i_serial].strip()
                masz_sap = row[i_masz_sap].strip() if i_masz_sap >= 0 else ""
                if masz_sap in self.excludes:
                    continue
                masz_opis = row[i_masz_opis].strip() if i_masz_opis >= 0 else ""
                judge = row[i_judge].strip()
                record = {
                    "data": parsed_dt,
                    "serial_no": serial,
                    "maszyna_sap": masz_sap,
                    "maszyna_opis": masz_opis,
                    "judge": judge,
                }
                entries_all.append(record)
                if str(judge).strip().upper() == "NOK":
                    entries_nok.append(record)
            except Exception:
                continue

        entries_all.sort(key=lambda x: x["data"])
        entries_nok.sort(key=lambda x: x["data"])
        kept = list(entries_nok)
        self.progress.emit(
            f"[Intranet] Filtered entries (NOK, in-range): {len(kept)} | all_in_range={len(entries_all)}"
        )

        fine_grain = (self.end_dt - self.start_dt).total_seconds() <= 48 * 3600
        series = defaultdict(int)
        rows_out: list[dict] = []
        for rec in kept:
            dt = rec["data"]
            serial = rec["serial_no"]
            judge = rec["judge"]
            bucket = dt.strftime("%Y-%m-%d %H:00") if fine_grain else dt.date().isoformat()
            series[bucket] += 1
            rows_out.append(rec)
            logging.getLogger(__name__).debug("[Intranet] rec serial=%s judge=%s", serial, judge)

        return {"series": dict(series), "rows": rows_out, "rows_all": entries_all}


__all__ = ["ScanWorker", "AnalyzeWorker", "IntranetWorker"]
