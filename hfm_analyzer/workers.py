"""Background worker threads responsible for I/O bound tasks."""

from __future__ import annotations

import glob
import logging
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Iterable, List
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QThread, pyqtSignal

from .models import FoundFile, ParamSnapshot

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


class AnalyzeWorker(QThread):
    """Parse backup XML files and extract parameter snapshots."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
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
            results: list[ParamSnapshot] = []
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
                        recs = future.result()
                        if recs:
                            results.extend(recs)
                    except Exception:
                        logging.getLogger(__name__).exception("[AnalyzeWorker] błąd podczas analizy pliku")
                        continue
            self.finished.emit(results)
        except Exception as exc:  # pragma: no cover - defensive programming
            self.error.emit(str(exc))

    # The parsing logic is intentionally kept private because it is always executed in worker threads.
    def _analyze_file(self, found_file: FoundFile) -> list[ParamSnapshot]:
        records: list[ParamSnapshot] = []
        if LET is not None:
            parser = LET.XMLParser(huge_tree=True, recover=True)  # type: ignore[arg-type]
            root = LET.parse(found_file.path, parser=parser).getroot()  # type: ignore[call-arg]
            iter_items = root.iter
        else:
            root = ET.parse(found_file.path).getroot()
            iter_items = root.iter

        program = ""
        for item in iter_items("Item"):
            if item.get("name") == "sgFileName":
                program = item.get("value") or ""
                break

        pin_map: dict[str, str] = {}
        a_hair = None
        a_kin = None
        for array in iter_items("Array"):
            name = array.get("name")
            if name == "aHairPinType" and a_hair is None:
                a_hair = array
            elif name == "aKinTable" and a_kin is None:
                a_kin = array
            if a_hair is not None and a_kin is not None:
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

        if a_kin is None:
            return records

        for struct in a_kin.iter("Struct"):
            struct_idx = struct.get("idx") or ""
            pin_name = pin_map.get(struct_idx, "")
            steps_arr = None
            for array in struct.iter("Array"):
                if array.get("name") == "Step":
                    steps_arr = array
                    break
            if steps_arr is None:
                continue

            steps = list(steps_arr.iter("Struct"))
            for step_index, step_el in enumerate(steps, start=1):
                r_pos = None
                bo_ax = None
                for array in step_el.iter("Array"):
                    name = array.get("name")
                    if name == "rPos":
                        r_pos = array
                    elif name == "boAxIncluded":
                        bo_ax = array
                    if r_pos is not None and bo_ax is not None:
                        break
                if r_pos is None or bo_ax is None:
                    continue
                pos_items = list(r_pos.iter("Item"))
                inc_items = list(bo_ax.iter("Item"))
                values = [0.0] * 7
                any_non_zero = False
                for idx in range(7):
                    include = 0
                    if idx < len(inc_items):
                        try:
                            include = int((inc_items[idx].get("value") or "0"))
                        except Exception:
                            include = 0
                    if include == 1 and idx < len(pos_items):
                        try:
                            value = float(pos_items[idx].get("value") or "0")
                        except Exception:
                            value = 0.0
                        values[idx] = value
                        if abs(value) > 1e-12:
                            any_non_zero = True
                if not any_non_zero:
                    continue

                step_speed = None
                try:
                    for item in step_el.iter("Item"):
                        if item.get("name") == "iOverride":
                            step_speed = float((item.get("value") or "0").strip())
                            break
                except Exception:
                    step_speed = None

                record_values = {
                    "X": values[0],
                    "Y": values[1],
                    "Angle": values[2],
                    "Rotation": values[3],
                    "Nose Translation": values[4],
                    "Nose Locking": values[5],
                    "Step Speed": step_speed if step_speed is not None else 0.0,
                    "Wire Feeding": values[6],
                }
                records.append(
                    ParamSnapshot(
                        dt=found_file.dt,
                        machine=found_file.machine,
                        program=program,
                        table=struct_idx,
                        pin=pin_name,
                        step=step_index,
                        values=record_values,
                        path=found_file.path,
                    )
                )
        return records


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
