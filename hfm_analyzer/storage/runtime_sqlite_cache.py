"""Runtime SQLite cache used to store analysis snapshots during the app session."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Iterator

from hfm_analyzer.constants import INDEX_PARAM_NAMES, PARAM_NAMES
from hfm_analyzer.models import (
    GripSnapshot,
    HairpinSnapshot,
    IndexSnapshot,
    NestSnapshot,
    ParamSnapshot,
)


class RuntimeSQLiteCache:
    """Temporary SQLite-backed cache for analysis snapshots."""

    def __init__(self, path: str | None = None) -> None:
        pid = os.getpid()
        if path is None:
            base_dir = tempfile.gettempdir()
            path = os.path.join(base_dir, f"hfm_analyzer_{pid}.sqlite")
        self.path = path
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()
        self._machine_cache: dict[str, int] = {}
        self._machine_lock = threading.Lock()
        conn = self._connect()
        self._init_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
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
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _ensure_machine(self, name: str) -> int:
        key = name or ""
        with self._machine_lock:
            cached = self._machine_cache.get(key)
            if cached is not None:
                return cached
        conn = self._get_connection()
        cur = conn.execute("SELECT id FROM machines WHERE name = ?", (key,))
        row = cur.fetchone()
        if row:
            machine_id = int(row["id"])
        else:
            cur = conn.execute("INSERT INTO machines(name) VALUES (?)", (key,))
            machine_id = int(cur.lastrowid)
        with self._machine_lock:
            self._machine_cache[key] = machine_id
        return machine_id

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
        cur = conn.execute(
            "SELECT id FROM files WHERE machine_id = ? AND path = ? AND mtime = ?",
            (machine_id, path, mtime),
        )
        row = cur.fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO files(machine_id, path, mtime) VALUES (?, ?, ?)",
            (machine_id, path, mtime),
        )
        return int(cur.lastrowid)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._get_connection()
        try:
            conn.execute("BEGIN")
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
        pin: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
        order_by_ts: bool = True,
    ) -> Iterator[ParamSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if pin is not None:
            conditions.append("s.pin = ?")
            params.append(pin)
        if step is not None:
            conditions.append("s.step = ?")
            params.append(step)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
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
        pin: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
    ) -> list[ParamSnapshot]:
        return list(self.iter_param_snapshots(machine=machine, pin=pin, step=step, dt=dt))

    def iter_index_snapshots(
        self,
        *,
        machine: str | None = None,
        table: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
    ) -> list[IndexSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if table is not None:
            conditions.append("s.table_name = ?")
            params.append(table)
        if step is not None:
            conditions.append("s.step = ?")
            params.append(step)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
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
        table: str | None = None,
        step: int | None = None,
        dt: datetime | None = None,
    ) -> list[IndexSnapshot]:
        return list(self.iter_index_snapshots(machine=machine, table=table, step=step, dt=dt))

    def fetch_struct_snapshots(
        self,
        prefix: str,
        *,
        machine: str | None = None,
        pin: str | None = None,
        dt: datetime | None = None,
    ) -> list[GripSnapshot | NestSnapshot | HairpinSnapshot]:
        conn = self._get_connection()
        conditions = []
        params: list[object] = []
        if machine is not None:
            conditions.append("m.name = ?")
            params.append(machine)
        if pin is not None:
            conditions.append("s.pin = ?")
            params.append(pin)
        if dt is not None:
            conditions.append("s.ts = ?")
            params.append(dt.isoformat())
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

    def fetch_param_line_hierarchy(self) -> dict[str, dict[str, set[str]]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.pin, s.step
            FROM param_snapshots s
            JOIN machines m ON s.machine_id = m.id
            GROUP BY m.name, s.pin, s.step
            """
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

    def fetch_index_line_hierarchy(self) -> dict[str, dict[str, set[str]]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.table_name, s.step
            FROM index_snapshots s
            JOIN machines m ON s.machine_id = m.id
            GROUP BY m.name, s.table_name, s.step
            """
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

    def fetch_param_card_groups(self) -> dict[str, list[datetime]]:
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT m.name AS machine, s.ts
            FROM param_snapshots s
            JOIN machines m ON s.machine_id = m.id
            GROUP BY m.name, s.ts
            """
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
