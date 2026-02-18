"""Runtime SQLite cache used to store analysis snapshots during the app session."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterable, Iterator

from hfm_analyzer.constants import INDEX_PARAM_NAMES, PARAM_NAMES
from hfm_analyzer.models import (
    FoundFile,
    GripSnapshot,
    HairpinSnapshot,
    IndexSnapshot,
    NestSnapshot,
    ParamSnapshot,
)


class RuntimeSQLiteCache:
    """SQLite-backed cache for analysis snapshots."""

    def __init__(self, path: str | None = None, *, persistent: bool = False) -> None:
        self.persistent = persistent
        pid = os.getpid()
        if path is None:
            base_dir = tempfile.gettempdir()
            path = os.path.join(base_dir, f"hfm_analyzer_{pid}.sqlite")
        self.path = path
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._machine_cache: dict[str, int] = {}
        self._machine_lock = threading.Lock()
        conn = self._connect()
        self._init_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        with self._conn_lock:
            self._connections.append(conn)
        return conn

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                machine_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                mtime REAL NOT NULL,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_files_unique ON files(machine_id, path, mtime);
            CREATE INDEX IF NOT EXISTS idx_files_machine ON files(machine_id);

            CREATE TABLE IF NOT EXISTS param_snapshots (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                program TEXT,
                table_name TEXT,
                pin TEXT,
                step INTEGER,
                ts TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_param_machine ON param_snapshots(machine_id);
            CREATE INDEX IF NOT EXISTS idx_param_ts ON param_snapshots(ts);
            CREATE INDEX IF NOT EXISTS idx_param_machine_ts ON param_snapshots(machine_id, ts);

            CREATE TABLE IF NOT EXISTS param_values (
                snapshot_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value REAL,
                included INTEGER,
                mode TEXT,
                PRIMARY KEY(snapshot_id, param_name),
                FOREIGN KEY(snapshot_id) REFERENCES param_snapshots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS index_snapshots (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                program TEXT,
                table_name TEXT,
                step INTEGER,
                ts TEXT,
                override REAL,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_index_machine ON index_snapshots(machine_id);
            CREATE INDEX IF NOT EXISTS idx_index_ts ON index_snapshots(ts);
            CREATE INDEX IF NOT EXISTS idx_index_machine_ts ON index_snapshots(machine_id, ts);

            CREATE TABLE IF NOT EXISTS index_values (
                snapshot_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value REAL,
                included INTEGER,
                mode TEXT,
                PRIMARY KEY(snapshot_id, param_name),
                FOREIGN KEY(snapshot_id) REFERENCES index_snapshots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS grip_snapshots (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                program TEXT,
                pin TEXT,
                ts TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_grip_machine ON grip_snapshots(machine_id);
            CREATE INDEX IF NOT EXISTS idx_grip_ts ON grip_snapshots(ts);
            CREATE INDEX IF NOT EXISTS idx_grip_machine_ts ON grip_snapshots(machine_id, ts);

            CREATE TABLE IF NOT EXISTS grip_values (
                snapshot_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT,
                PRIMARY KEY(snapshot_id, param_name),
                FOREIGN KEY(snapshot_id) REFERENCES grip_snapshots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS nest_snapshots (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                program TEXT,
                pin TEXT,
                ts TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_nest_machine ON nest_snapshots(machine_id);
            CREATE INDEX IF NOT EXISTS idx_nest_ts ON nest_snapshots(ts);
            CREATE INDEX IF NOT EXISTS idx_nest_machine_ts ON nest_snapshots(machine_id, ts);

            CREATE TABLE IF NOT EXISTS nest_values (
                snapshot_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT,
                PRIMARY KEY(snapshot_id, param_name),
                FOREIGN KEY(snapshot_id) REFERENCES nest_snapshots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS hairpin_snapshots (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                machine_id INTEGER NOT NULL,
                program TEXT,
                pin TEXT,
                ts TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_hairpin_machine ON hairpin_snapshots(machine_id);
            CREATE INDEX IF NOT EXISTS idx_hairpin_ts ON hairpin_snapshots(ts);
            CREATE INDEX IF NOT EXISTS idx_hairpin_machine_ts ON hairpin_snapshots(machine_id, ts);

            CREATE TABLE IF NOT EXISTS hairpin_values (
                snapshot_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT,
                PRIMARY KEY(snapshot_id, param_name),
                FOREIGN KEY(snapshot_id) REFERENCES hairpin_snapshots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS intranet_rows (
                id INTEGER PRIMARY KEY,
                line_id INTEGER,
                ts TEXT NOT NULL,
                serial_no TEXT NOT NULL,
                judge TEXT,
                maszyna_sap TEXT,
                maszyna_opis TEXT,
                UNIQUE(line_id, ts, serial_no, judge, maszyna_sap, maszyna_opis)
            );
            CREATE INDEX IF NOT EXISTS idx_intranet_ts ON intranet_rows(ts);
            CREATE INDEX IF NOT EXISTS idx_intranet_serial ON intranet_rows(serial_no);

            CREATE TABLE IF NOT EXISTS hour_buckets (
                id INTEGER PRIMARY KEY,
                machine_id INTEGER NOT NULL,
                ts TEXT NOT NULL,
                UNIQUE(machine_id, ts),
                FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_hour_buckets_ts ON hour_buckets(ts);
            """
        )

    def close(self) -> None:
        with self._conn_lock:
            conns = list(self._connections)
            self._connections.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                pass
        if not self.persistent:
            try:
                os.remove(self.path)
            except FileNotFoundError:
                pass
            except Exception:
                pass

    def reset(self) -> None:
        """Clear all cached data while keeping the database file."""
        conn = self._get_connection()
        with self._write_lock:
            conn.executescript(
                """
                DELETE FROM param_values;
                DELETE FROM param_snapshots;
                DELETE FROM index_values;
                DELETE FROM index_snapshots;
                DELETE FROM grip_values;
                DELETE FROM grip_snapshots;
                DELETE FROM nest_values;
                DELETE FROM nest_snapshots;
                DELETE FROM hairpin_values;
                DELETE FROM hairpin_snapshots;
                DELETE FROM hour_buckets;
                DELETE FROM files;
                DELETE FROM machines;
                """
            )
        with self._machine_lock:
            self._machine_cache.clear()

    @staticmethod
    def purge_older_than(path: str, cutoff: datetime) -> dict[str, int]:
        """Delete data older than cutoff from a persistent database file."""
        results: dict[str, int] = {}
        if not path or not os.path.exists(path):
            return results
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        cutoff_ts = cutoff.isoformat()
        try:
            for table in (
                "param_snapshots",
                "index_snapshots",
                "grip_snapshots",
                "nest_snapshots",
                "hairpin_snapshots",
                "intranet_rows",
                "hour_buckets",
            ):
                row = conn.execute(
                    f"SELECT COUNT(*) AS cnt FROM {table} WHERE ts < ?",
                    (cutoff_ts,),
                ).fetchone()
                results[table] = int(row["cnt"]) if row else 0

            conn.execute("BEGIN IMMEDIATE")
            for table in (
                "param_snapshots",
                "index_snapshots",
                "grip_snapshots",
                "nest_snapshots",
                "hairpin_snapshots",
                "intranet_rows",
                "hour_buckets",
            ):
                conn.execute(f"DELETE FROM {table} WHERE ts < ?", (cutoff_ts,))

            conn.execute(
                """
                DELETE FROM files
                WHERE id NOT IN (
                    SELECT DISTINCT file_id FROM param_snapshots
                    UNION
                    SELECT DISTINCT file_id FROM index_snapshots
                    UNION
                    SELECT DISTINCT file_id FROM grip_snapshots
                    UNION
                    SELECT DISTINCT file_id FROM nest_snapshots
                    UNION
                    SELECT DISTINCT file_id FROM hairpin_snapshots
                )
                """
            )
            conn.execute(
                "DELETE FROM machines WHERE id NOT IN (SELECT DISTINCT machine_id FROM files)"
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return results

    def _ensure_machine(self, name: str) -> int:
        key = name or ""
        with self._machine_lock:
            cached = self._machine_cache.get(key)
            if cached is not None:
                return cached
        conn = self._get_connection()
        with self._write_lock:
            cur = conn.execute("SELECT id FROM machines WHERE name = ?", (key,))
            row = cur.fetchone()
            if row:
                machine_id = int(row["id"])
            else:
                conn.execute("INSERT OR IGNORE INTO machines(name) VALUES (?)", (key,))
                cur = conn.execute("SELECT id FROM machines WHERE name = ?", (key,))
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("Nie udało się zapisać maszyny w cache SQLite.")
                machine_id = int(row["id"])
        with self._machine_lock:
            self._machine_cache[key] = machine_id
        return machine_id

    @staticmethod
    def _hour_bucket_ts(dt: datetime) -> str:
        bucket = dt.replace(minute=0, second=0, microsecond=0)
        return bucket.isoformat()

    def has_hour_bucket(self, machine: str, dt: datetime) -> bool:
        machine_id = self._ensure_machine(machine)
        conn = self._get_connection()
        bucket_ts = self._hour_bucket_ts(dt)
        cur = conn.execute(
            "SELECT 1 FROM hour_buckets WHERE machine_id = ? AND ts = ?",
            (machine_id, bucket_ts),
        )
        if cur.fetchone() is not None:
            return True

        try:
            start = datetime.fromisoformat(bucket_ts)
        except Exception:
            return False
        end = start + timedelta(hours=1)
        start_ts = start.isoformat()
        end_ts = end.isoformat()
        for table in (
            "param_snapshots",
            "index_snapshots",
            "grip_snapshots",
            "nest_snapshots",
            "hairpin_snapshots",
        ):
            cur = conn.execute(
                f"SELECT 1 FROM {table} WHERE machine_id = ? AND ts >= ? AND ts < ? LIMIT 1",
                (machine_id, start_ts, end_ts),
            )
            if cur.fetchone() is not None:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO hour_buckets(machine_id, ts) VALUES (?, ?)",
                        (machine_id, bucket_ts),
                    )
                except Exception:
                    pass
                return True
        return False

    def record_hour_bucket(self, machine: str, dt: datetime) -> None:
        machine_id = self._ensure_machine(machine)
        conn = self._get_connection()
        bucket_ts = self._hour_bucket_ts(dt)
        with self._write_lock:
            conn.execute(
                "INSERT OR IGNORE INTO hour_buckets(machine_id, ts) VALUES (?, ?)",
                (machine_id, bucket_ts),
            )

    def has_file(self, machine: str, path: str, mtime: float) -> bool:
        machine_id = self._ensure_machine(machine)
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT 1 FROM files WHERE machine_id = ? AND path = ? AND mtime = ?",
            (machine_id, path, mtime),
        )
        return cur.fetchone() is not None

    def record_file(self, machine: str, path: str, mtime: float) -> int:
        machine_id = self._ensure_machine(machine)
        conn = self._get_connection()
        with self._write_lock:
            cur = conn.execute(
                "SELECT id FROM files WHERE machine_id = ? AND path = ? AND mtime = ?",
                (machine_id, path, mtime),
            )
            row = cur.fetchone()
            if row:
                return int(row["id"])
            conn.execute(
                "INSERT OR IGNORE INTO files(machine_id, path, mtime) VALUES (?, ?, ?)",
                (machine_id, path, mtime),
            )
            cur = conn.execute(
                "SELECT id FROM files WHERE machine_id = ? AND path = ? AND mtime = ?",
                (machine_id, path, mtime),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Nie udało się zapisać pliku w cache SQLite.")
            return int(row["id"])

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._get_connection()
        with self._write_lock:
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
            except Exception:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def insert_param_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[ParamSnapshot],
    ) -> int:
        machine_id = self._ensure_machine(machine)
        total = 0
        with self._transaction() as conn:
            for snap in snapshots:
                cur = conn.execute(
                    """
                    INSERT INTO param_snapshots(file_id, machine_id, program, table_name, pin, step, ts)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        machine_id,
                        snap.program,
                        snap.table,
                        snap.pin,
                        snap.step,
                        snap.dt.isoformat(),
                    ),
                )
                snap_id = int(cur.lastrowid)
                values = []
                for name, value in snap.values.items():
                    included = snap.included.get(name) if name in snap.included else None
                    mode = snap.modes.get(name) if name in snap.modes else None
                    values.append((snap_id, name, value, int(included) if included is not None else None, mode))
                if values:
                    conn.executemany(
                        """
                        INSERT INTO param_values(snapshot_id, param_name, param_value, included, mode)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                total += 1
        return total

    def insert_index_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[IndexSnapshot],
    ) -> int:
        machine_id = self._ensure_machine(machine)
        total = 0
        with self._transaction() as conn:
            for snap in snapshots:
                cur = conn.execute(
                    """
                    INSERT INTO index_snapshots(file_id, machine_id, program, table_name, step, ts, override)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        machine_id,
                        snap.program,
                        snap.table,
                        snap.step,
                        snap.dt.isoformat(),
                        snap.override,
                    ),
                )
                snap_id = int(cur.lastrowid)
                values = []
                for name, value in snap.values.items():
                    included = snap.included.get(name) if name in snap.included else None
                    mode = snap.modes.get(name) if name in snap.modes else None
                    values.append((snap_id, name, value, int(included) if included is not None else None, mode))
                if values:
                    conn.executemany(
                        """
                        INSERT INTO index_values(snapshot_id, param_name, param_value, included, mode)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                total += 1
        return total

    def insert_grip_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[GripSnapshot],
    ) -> int:
        return self._insert_struct_snapshots(file_id, machine, snapshots, "grip")

    def insert_nest_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[NestSnapshot],
    ) -> int:
        return self._insert_struct_snapshots(file_id, machine, snapshots, "nest")

    def insert_hairpin_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[HairpinSnapshot],
    ) -> int:
        return self._insert_struct_snapshots(file_id, machine, snapshots, "hairpin")

    def _insert_struct_snapshots(
        self,
        file_id: int,
        machine: str,
        snapshots: Iterable[GripSnapshot | NestSnapshot | HairpinSnapshot],
        prefix: str,
    ) -> int:
        machine_id = self._ensure_machine(machine)
        total = 0
        with self._transaction() as conn:
            for snap in snapshots:
                cur = conn.execute(
                    f"""
                    INSERT INTO {prefix}_snapshots(file_id, machine_id, program, pin, ts)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        machine_id,
                        snap.program,
                        snap.pin,
                        snap.dt.isoformat(),
                    ),
                )
                snap_id = int(cur.lastrowid)
                values = [(snap_id, name, value) for name, value in snap.values.items()]
                if values:
                    conn.executemany(
                        f"""
                        INSERT INTO {prefix}_values(snapshot_id, param_name, param_value)
                        VALUES (?, ?, ?)
                        """,
                        values,
                    )
                total += 1
        return total

    def iter_param_snapshots(
        self,
        *,
        machine: str | None = None,
        machines: Iterable[str] | None = None,
        pin: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        order_by_ts: bool = True,
    ) -> Iterator[ParamSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if pin is not None:
            conditions.append("s.pin = ?")
            params.append(pin)
        if step is not None:
            conditions.append("s.step = ?")
            params.append(step)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order = "ORDER BY s.ts" if order_by_ts else ""
        query = (
            "SELECT s.id, s.ts, m.name AS machine, s.program, s.table_name, s.pin, s.step, f.path, "
            "v.param_name, v.param_value, v.included, v.mode "
            "FROM param_snapshots s "
            "JOIN machines m ON s.machine_id = m.id "
            "JOIN files f ON s.file_id = f.id "
            "JOIN param_values v ON v.snapshot_id = s.id "
            f"{where} {order}"
        )
        rows = conn.execute(query, params)
        current_id = None
        snapshot: ParamSnapshot | None = None
        values: dict[str, float | None] = {}
        included: dict[str, bool] = {name: False for name in PARAM_NAMES}
        modes: dict[str, str] = {name: "ABS" for name in PARAM_NAMES}
        for row in rows:
            snap_id = row["id"]
            if current_id is None or snap_id != current_id:
                if snapshot is not None:
                    snapshot.values = values
                    snapshot.included = included
                    snapshot.modes = modes
                    yield snapshot
                current_id = snap_id
                values = {}
                included = {name: False for name in PARAM_NAMES}
                modes = {name: "ABS" for name in PARAM_NAMES}
                ts = datetime.fromisoformat(row["ts"]) if row["ts"] else datetime.min
                snapshot = ParamSnapshot(
                    dt=ts,
                    machine=row["machine"] or "",
                    program=row["program"] or "",
                    table=row["table_name"] or "",
                    pin=row["pin"] or "",
                    step=row["step"],
                    values={},
                    included={},
                    modes={},
                    path=row["path"] or "",
                )
            name = row["param_name"]
            values[name] = row["param_value"]
            if name in included and row["included"] is not None:
                included[name] = bool(row["included"])
            if name in modes and row["mode"]:
                modes[name] = row["mode"]
        if snapshot is not None:
            snapshot.values = values
            snapshot.included = included
            snapshot.modes = modes
            yield snapshot

    def fetch_param_snapshots(
        self,
        *,
        machine: str | None = None,
        machines: Iterable[str] | None = None,
        pin: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[ParamSnapshot]:
        return list(
            self.iter_param_snapshots(
                machine=machine,
                machines=machines,
                pin=pin,
                step=step,
                dt=dt,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        )

    def iter_index_snapshots(
        self,
        *,
        machine: str | None = None,
        machines: Iterable[str] | None = None,
        table: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[IndexSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if table is not None:
            conditions.append("s.table_name = ?")
            params.append(table)
        if step is not None:
            conditions.append("s.step = ?")
            params.append(step)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = (
            "SELECT s.id, s.ts, m.name AS machine, s.program, s.table_name, s.step, s.override, f.path, "
            "v.param_name, v.param_value, v.included, v.mode "
            "FROM index_snapshots s "
            "JOIN machines m ON s.machine_id = m.id "
            "JOIN files f ON s.file_id = f.id "
            "JOIN index_values v ON v.snapshot_id = s.id "
            f"{where} ORDER BY s.ts"
        )
        rows = conn.execute(query, params)
        current_id = None
        snapshot: IndexSnapshot | None = None
        values: dict[str, float] = {}
        included: dict[str, bool] = {name: False for name in INDEX_PARAM_NAMES}
        modes: dict[str, str] = {name: "ABS" for name in INDEX_PARAM_NAMES}
        for row in rows:
            snap_id = row["id"]
            if current_id is None or snap_id != current_id:
                if snapshot is not None:
                    snapshot.values = values
                    snapshot.included = included
                    snapshot.modes = modes
                    yield snapshot
                current_id = snap_id
                values = {}
                included = {name: False for name in INDEX_PARAM_NAMES}
                modes = {name: "ABS" for name in INDEX_PARAM_NAMES}
                ts = datetime.fromisoformat(row["ts"]) if row["ts"] else datetime.min
                snapshot = IndexSnapshot(
                    dt=ts,
                    machine=row["machine"] or "",
                    program=row["program"] or "",
                    table=row["table_name"] or "",
                    step=row["step"],
                    values={},
                    included={},
                    modes={},
                    override=row["override"],
                    path=row["path"] or "",
                )
            name = row["param_name"]
            values[name] = row["param_value"]
            if name in included and row["included"] is not None:
                included[name] = bool(row["included"])
            if name in modes and row["mode"]:
                modes[name] = row["mode"]
        if snapshot is not None:
            snapshot.values = values
            snapshot.included = included
            snapshot.modes = modes
            yield snapshot

    def fetch_index_snapshots_list(
        self,
        *,
        machine: str | None = None,
        machines: Iterable[str] | None = None,
        table: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[IndexSnapshot]:
        return list(
            self.iter_index_snapshots(
                machine=machine,
                machines=machines,
                table=table,
                step=step,
                dt=dt,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        )

    def fetch_struct_snapshots(
        self,
        prefix: str,
        *,
        machine: str | None = None,
        machines: Iterable[str] | None = None,
        pin: str | None = None,
        dt: datetime | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[GripSnapshot | NestSnapshot | HairpinSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if pin is not None:
            conditions.append("s.pin = ?")
            params.append(pin)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = (
            f"SELECT s.id, s.ts, m.name AS machine, s.program, s.pin, f.path, "
            f"v.param_name, v.param_value "
            f"FROM {prefix}_snapshots s "
            f"JOIN machines m ON s.machine_id = m.id "
            f"JOIN files f ON s.file_id = f.id "
            f"JOIN {prefix}_values v ON v.snapshot_id = s.id "
            f"{where} ORDER BY s.ts"
        )
        rows = conn.execute(query, params)
        current_id = None
        snapshot = None
        values: dict[str, str] = {}
        snapshots: list[GripSnapshot | NestSnapshot | HairpinSnapshot] = []
        factory = {
            "grip": GripSnapshot,
            "nest": NestSnapshot,
            "hairpin": HairpinSnapshot,
        }[prefix]
        for row in rows:
            snap_id = row["id"]
            if current_id is None or snap_id != current_id:
                if snapshot is not None:
                    snapshot.values = values
                    snapshots.append(snapshot)
                current_id = snap_id
                values = {}
                ts = datetime.fromisoformat(row["ts"]) if row["ts"] else datetime.min
                snapshot = factory(
                    dt=ts,
                    machine=row["machine"] or "",
                    program=row["program"] or "",
                    pin=row["pin"] or "",
                    values={},
                    path=row["path"] or "",
                )
            values[row["param_name"]] = row["param_value"]
        if snapshot is not None:
            snapshot.values = values
            snapshots.append(snapshot)
        return snapshots

    def fetch_struct_value_keys(self, prefix: str) -> list[str]:
        conn = self._get_connection()
        rows = conn.execute(
            f"SELECT DISTINCT param_name FROM {prefix}_values ORDER BY param_name"
        )
        return [row["param_name"] for row in rows]

    def fetch_machine_names(self) -> list[str]:
        conn = self._get_connection()
        rows = conn.execute("SELECT name FROM machines ORDER BY name").fetchall()
        return [row["name"] for row in rows if row["name"]]

    @staticmethod
    def _parse_file_dt(path: str) -> datetime | None:
        try:
            name = os.path.basename(path or "")
        except Exception:
            name = path or ""
        if not name:
            return None
        parts = name.split("_")
        if len(parts) < 3:
            return None
        dt_str = parts[1] + "_" + parts[2].replace(".xml", "")
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S")
        except Exception:
            return None

    def fetch_files(
        self,
        *,
        machines: Iterable[str] | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> list[FoundFile]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            "SELECT f.path, m.name AS machine FROM files f JOIN machines m ON f.machine_id = m.id"
            + where,
            params,
        )
        results: list[FoundFile] = []
        for row in rows:
            path = row["path"] or ""
            dt = self._parse_file_dt(path)
            if dt is None:
                continue
            if start_dt is not None and dt < start_dt:
                continue
            if end_dt is not None and dt > end_dt:
                continue
            results.append(FoundFile(machine=row["machine"] or "", dt=dt, path=path))
        results.sort(key=lambda r: (r.dt, r.machine, r.path))
        return results

    def insert_intranet_rows(
        self,
        rows: Iterable[dict],
        *,
        line_id: int | None = None,
    ) -> int:
        items = list(rows or [])
        if not items:
            return 0
        try:
            lid = int(line_id or 0)
        except Exception:
            lid = 0
        values: list[tuple[object, ...]] = []
        for rec in items:
            if not isinstance(rec, dict):
                continue
            dt = rec.get("data")
            ts = ""
            if isinstance(dt, datetime):
                ts = dt.isoformat()
            elif dt:
                try:
                    ts = datetime.fromisoformat(str(dt)).isoformat()
                except Exception:
                    ts = ""
            if not ts:
                continue
            serial = str(rec.get("serial_no", "") or "").strip()
            if not serial:
                continue
            judge = str(rec.get("judge", "") or "").strip()
            masz_sap = str(rec.get("maszyna_sap", "") or "").strip()
            masz_opis = str(rec.get("maszyna_opis", "") or "").strip()
            values.append((lid, ts, serial, judge, masz_sap, masz_opis))
        if not values:
            return 0
        with self._transaction() as conn:
            before = conn.total_changes
            conn.executemany(
                """
                INSERT OR IGNORE INTO intranet_rows
                (line_id, ts, serial_no, judge, maszyna_sap, maszyna_opis)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            inserted = conn.total_changes - before
        return int(inserted)

    def fetch_intranet_rows(
        self,
        *,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        line_id: int | None = None,
    ) -> list[dict]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if line_id is not None:
            try:
                conditions.append("line_id = ?")
                params.append(int(line_id))
            except Exception:
                pass
        if start_dt is not None:
            conditions.append("ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            "SELECT ts, serial_no, judge, maszyna_sap, maszyna_opis FROM intranet_rows"
            + where
            + " ORDER BY ts",
            params,
        )
        results: list[dict] = []
        for row in rows:
            ts = row["ts"]
            try:
                dt = datetime.fromisoformat(ts) if ts else None
            except Exception:
                dt = None
            if dt is None:
                continue
            results.append(
                {
                    "data": dt,
                    "serial_no": row["serial_no"],
                    "judge": row["judge"],
                    "maszyna_sap": row["maszyna_sap"],
                    "maszyna_opis": row["maszyna_opis"],
                }
            )
        return results

    def fetch_time_bounds(
        self,
        *,
        machines: Iterable[str] | None = None,
    ) -> tuple[datetime | None, datetime | None]:
        conn = self._get_connection()
        min_dt: datetime | None = None
        max_dt: datetime | None = None
        machine_list = [m for m in (machines or []) if m]
        tables = (
            "param_snapshots",
            "index_snapshots",
            "grip_snapshots",
            "nest_snapshots",
            "hairpin_snapshots",
        )
        for table in tables:
            params: list[object] = []
            join = ""
            where = ""
            if machine_list:
                join = "JOIN machines m ON s.machine_id = m.id"
                placeholders = ", ".join("?" for _ in machine_list)
                where = f"WHERE m.name IN ({placeholders})"
                params.extend(machine_list)
            row = conn.execute(
                f"SELECT MIN(s.ts) AS min_ts, MAX(s.ts) AS max_ts FROM {table} s {join} {where}",
                params,
            ).fetchone()
            if not row:
                continue
            min_ts = row["min_ts"]
            max_ts = row["max_ts"]
            try:
                if min_ts:
                    cur_min = datetime.fromisoformat(min_ts)
                    if min_dt is None or cur_min < min_dt:
                        min_dt = cur_min
                if max_ts:
                    cur_max = datetime.fromisoformat(max_ts)
                    if max_dt is None or cur_max > max_dt:
                        max_dt = cur_max
            except Exception:
                continue
        return min_dt, max_dt

    def fetch_param_line_hierarchy(
        self,
        *,
        machines: Iterable[str] | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> dict[str, dict[str, set[str]]]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.pin, s.step
            FROM param_snapshots s
            JOIN machines m ON s.machine_id = m.id
            """
            + where
            + """
            GROUP BY m.name, s.pin, s.step
            """,
            params,
        )
        hierarchy: dict[str, dict[str, set[str]]] = {}
        for row in rows:
            machine = (row["machine"] or "").strip()
            pin = (row["pin"] or "").strip()
            step = row["step"]
            if not machine:
                continue
            machine_entry = hierarchy.setdefault(machine, {})
            step_set = machine_entry.setdefault(pin, set())
            if step is not None:
                step_set.add(str(step))
        return hierarchy

    def fetch_index_line_hierarchy(
        self,
        *,
        machines: Iterable[str] | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> dict[str, dict[str, set[str]]]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.table_name, s.step
            FROM index_snapshots s
            JOIN machines m ON s.machine_id = m.id
            """
            + where
            + """
            GROUP BY m.name, s.table_name, s.step
            """,
            params,
        )
        hierarchy: dict[str, dict[str, set[str]]] = {}
        for row in rows:
            machine = (row["machine"] or "").strip()
            table = (row["table_name"] or "").strip()
            step = row["step"]
            if not machine:
                continue
            machine_entry = hierarchy.setdefault(machine, {})
            step_set = machine_entry.setdefault(table, set())
            if step is not None:
                step_set.add(str(step))
        return hierarchy

    def fetch_param_card_groups(
        self,
        *,
        machines: Iterable[str] | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> dict[str, list[datetime]]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machines:
            machine_list = [m for m in machines if m]
            if machine_list:
                placeholders = ", ".join("?" for _ in machine_list)
                conditions.append(f"m.name IN ({placeholders})")
                params.extend(machine_list)
        if start_dt is not None:
            conditions.append("s.ts >= ?")
            params.append(start_dt.isoformat())
        if end_dt is not None:
            conditions.append("s.ts <= ?")
            params.append(end_dt.isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.ts
            FROM param_snapshots s
            JOIN machines m ON s.machine_id = m.id
            """
            + where
            + """
            GROUP BY m.name, s.ts
            """,
            params,
        )
        groups: dict[str, list[datetime]] = {}
        for row in rows:
            machine = row["machine"] or ""
            ts = row["ts"]
            if not ts:
                continue
            dt = datetime.fromisoformat(ts)
            groups.setdefault(machine, []).append(dt)
        return groups

    def stats(self) -> dict[str, int]:
        conn = self._get_connection()
        stats = {}
        for name, table in (
            ("params", "param_snapshots"),
            ("index", "index_snapshots"),
            ("hp_grip", "grip_snapshots"),
            ("nest", "nest_snapshots"),
            ("hairpin", "hairpin_snapshots"),
            ("files", "files"),
        ):
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
            stats[name] = int(row["cnt"]) if row else 0
        return stats
