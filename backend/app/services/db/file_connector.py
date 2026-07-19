"""FileConnector — in-memory SQLite built from a databases/<db_name>/ folder's SQL files.

Implements the DBConnector protocol without any database server:
- Schema and seed data are transpiled MySQL -> SQLite via sqlglot at startup.
- introspect() builds the DBProfile from the parsed schema AST (not from a live DB).
- execute_read() returns real rows from the seed data, read-only, forced LIMIT.

The schema/data files are discovered by glob (*_schema.sql / *_data.sql) within
the database's folder, following the NN_<db_name>_<type>.ext naming convention.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
import threading
from typing import Any

import sqlglot
from sqlglot import exp

from backend.app.config import settings
from backend.app.models.envelope import ColumnInfo, DBProfile, TableInfo
from backend.app.services import clock


def _mysql_to_sqlite(sql: str) -> str:
    """Transpile agent-emitted MySQL to SQLite for execution/EXPLAIN.

    sqlglot (30.x) leaves MySQL date arithmetic untranspiled for SQLite —
    `DATE_SUB(CURDATE(), INTERVAL 8 MONTH)` becomes a nonexistent 3-arg
    DATE_SUB() call — so any "last N months/days" query would fail EXPLAIN
    and be blocked by the syntax-verification layer. Rewrite DATE_SUB/DATE_ADD
    at the AST level into SQLite date-modifier form: DATE(x, '-8 month').

    CURDATE()/CURRENT_TIMESTAMP are kept as calls to the registered CURDATE/NOW
    functions (see _register_mysql_functions) rather than transpiled to SQLite's
    CURRENT_DATE keyword: the registered functions read services/clock.py, so a
    frozen clock (IDI_FREEZE_NOW) governs executed SQL too — the keyword would
    silently read the system clock instead.
    """
    tree = sqlglot.parse_one(sql, read="mysql")

    def rewrite(node: exp.Expression) -> exp.Expression:
        if isinstance(node, (exp.DateSub, exp.DateAdd)):
            sign = "-" if isinstance(node, exp.DateSub) else "+"
            qty = node.expression.name
            unit = (node.text("unit") or "day").lower()
            # Recurse into the date argument ourselves: transform() does not
            # descend into the freshly built DATE() node, so an inner
            # CURDATE()/NOW() would otherwise render as SQLite's CURRENT_DATE
            # keyword — real system clock, silently ignoring IDI_FREEZE_NOW.
            inner = node.this.transform(rewrite)
            return exp.func("DATE", inner, exp.Literal.string(f"{sign}{qty} {unit}"))
        if isinstance(node, exp.CurrentDate):
            return exp.func("CURDATE")
        if isinstance(node, exp.CurrentTimestamp):
            return exp.func("NOW")
        return node

    return tree.transform(rewrite).sql(dialect="sqlite")


class FileConnector:
    def __init__(self, db_name: str) -> None:
        self.db_name = db_name
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._db_dir = os.path.join(settings.repo_root, settings.databases_dir, db_name)
        self._schema_asts: list[exp.Expression] = []

    @property
    def db_dir(self) -> str:
        return self._db_dir

    def _find_one(self, pattern: str) -> str:
        matches = glob.glob(os.path.join(self._db_dir, pattern))
        if len(matches) != 1:
            raise FileNotFoundError(
                f"Expected exactly one '{pattern}' file in {self._db_dir}, found {len(matches)}."
            )
        return matches[0]

    # -- lifecycle -------------------------------------------------------------

    def connect(self) -> None:
        """Build the in-memory DB once: transpile schema + data, execute both."""
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._register_mysql_functions(self._conn)
        self._load_sql_file(self._find_one("*_schema.sql"), keep_asts=True)
        self._load_sql_file(self._find_one("*_data.sql"))

    @staticmethod
    def _register_mysql_functions(conn: sqlite3.Connection) -> None:
        """MySQL date functions that sqlglot leaves untranspiled for SQLite
        (YEAR/MONTH/DAY/NOW as of sqlglot 30.x). Agents emit MySQL, so without
        these any date-filtered query fails EXPLAIN and gets blocked by the
        syntax-verification layer.

        NOW/CURDATE read services/clock.py (evaluated at query time, not
        registration time), so the whole pipeline — prompts and executed SQL —
        shares one clock and honors an IDI_FREEZE_NOW override."""

        def _part(value: Any, start: int, end: int) -> int | None:
            s = str(value)
            return int(s[start:end]) if value is not None and s[start:end].isdigit() else None

        conn.create_function("YEAR", 1, lambda v: _part(v, 0, 4), deterministic=True)
        conn.create_function("MONTH", 1, lambda v: _part(v, 5, 7), deterministic=True)
        conn.create_function("DAY", 1, lambda v: _part(v, 8, 10), deterministic=True)
        conn.create_function("NOW", 0, clock.now_str)
        conn.create_function("CURDATE", 0, clock.today_str)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
        self._conn = None

    # Column constraints with no SQLite equivalent — stripped before execution.
    _SQLITE_INCOMPATIBLE_CONSTRAINTS = (
        exp.AutoIncrementColumnConstraint,
        exp.OnUpdateColumnConstraint,
        exp.CollateColumnConstraint,
        exp.CharacterSetColumnConstraint,
        exp.CommentColumnConstraint,
    )

    def _sqlite_ddl(self, create: exp.Create) -> str:
        """Render a MySQL CREATE TABLE as SQLite-executable DDL.

        Drops what SQLite rejects: ENGINE/CHARSET/COMMENT table properties,
        AUTO_INCREMENT / ON UPDATE column constraints, named inline
        UNIQUE KEY / KEY index definitions, and ENUM types (become TEXT).
        """
        create = create.copy()
        create.args.pop("properties", None)
        schema = create.this
        if isinstance(schema, exp.Schema):
            # AUTO_INCREMENT columns must become INTEGER PRIMARY KEY (SQLite's
            # rowid alias) so INSERTs that omit them auto-assign ids.
            auto_inc_cols = {
                defn.name
                for defn in schema.expressions
                if isinstance(defn, exp.ColumnDef)
                and any(
                    isinstance(c.kind, exp.AutoIncrementColumnConstraint) for c in defn.constraints
                )
            }
            defs = []
            for defn in schema.expressions:
                # Named inline UNIQUE/INDEX definitions are not valid SQLite DDL.
                if isinstance(defn, (exp.UniqueColumnConstraint, exp.IndexColumnConstraint)):
                    continue
                # Drop the table-level PK of an auto-increment column (moved inline).
                if (
                    isinstance(defn, exp.PrimaryKey)
                    and {c.name for c in defn.expressions} <= auto_inc_cols
                ):
                    continue
                if isinstance(defn, exp.ColumnDef):
                    if defn.name in auto_inc_cols:
                        defn.set("kind", exp.DataType.build("INTEGER"))
                        defn.set(
                            "constraints",
                            [exp.ColumnConstraint(kind=exp.PrimaryKeyColumnConstraint())],
                        )
                        defs.append(defn)
                        continue
                    kind = defn.args.get("kind")
                    if kind is not None and kind.this == exp.DataType.Type.ENUM:
                        defn.set("kind", exp.DataType.build("TEXT"))
                    defn.set(
                        "constraints",
                        [
                            c
                            for c in defn.constraints
                            if not isinstance(c.kind, self._SQLITE_INCOMPATIBLE_CONSTRAINTS)
                        ],
                    )
                defs.append(defn)
            schema.set("expressions", defs)
        return create.sql(dialect="sqlite")

    def _load_sql_file(self, path: str, keep_asts: bool = False) -> None:
        filename = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        # Strip MySQL-only directives sqlglot does not need to see
        raw = re.sub(
            r"(?ims)^\s*(SET|USE|CREATE\s+DATABASE|DROP\s+DATABASE|LOCK|UNLOCK)\b.*?;", "", raw
        )
        statements = sqlglot.parse(raw, dialect="mysql")
        cur = self._conn.cursor()
        for stmt in statements:
            if stmt is None:
                continue
            if isinstance(stmt, exp.Create):
                if stmt.kind != "TABLE":
                    continue  # CREATE DATABASE etc. — nothing to execute in SQLite
                if keep_asts:
                    # Keep the untransformed AST so introspect() reports MySQL types.
                    self._schema_asts.append(stmt)
                exec_sql = self._sqlite_ddl(stmt)
            else:
                exec_sql = stmt.sql(dialect="sqlite")
            try:
                cur.execute(exec_sql)
            except sqlite3.Error as e:
                # Log and continue: FK pragmas / engine clauses may not translate.
                print(f"[FileConnector] skipped statement in {filename}: {e}")
        self._conn.commit()
        cur.close()

    # -- introspection (from the parsed schema, not the live DB) ----------------

    def introspect(self) -> DBProfile:
        self.connect()
        tables: list[TableInfo] = []
        edges: list[tuple[str, str]] = []

        for create in self._schema_asts:
            tname = (
                create.this.this.name if isinstance(create.this, exp.Schema) else create.this.name
            )
            schema = create.this if isinstance(create.this, exp.Schema) else None
            columns: list[ColumnInfo] = []
            pks: set[str] = set()
            fks: dict[str, str] = {}

            if schema:
                for defn in schema.expressions:
                    if isinstance(defn, exp.ColumnDef):
                        constraints = [c.kind for c in defn.constraints]
                        if any(isinstance(k, exp.PrimaryKeyColumnConstraint) for k in constraints):
                            pks.add(defn.name)
                        columns.append(
                            ColumnInfo(
                                name=defn.name,
                                data_type=(
                                    defn.args["kind"].sql(dialect="mysql")
                                    if defn.args.get("kind")
                                    else "unknown"
                                ),
                                # Explicit NULL: NotNullColumnConstraint with allow_null=True.
                                is_nullable=not any(
                                    isinstance(k, exp.NotNullColumnConstraint)
                                    and not k.args.get("allow_null")
                                    for k in constraints
                                ),
                            )
                        )
                    elif isinstance(defn, exp.PrimaryKey):
                        pks.update(c.name for c in defn.expressions)
                    elif isinstance(defn, (exp.ForeignKey, exp.Constraint)):
                        # FKs may be bare or wrapped in a named CONSTRAINT.
                        for fk in defn.find_all(exp.ForeignKey):
                            src_cols = [c.name for c in fk.expressions]
                            ref = fk.args.get("reference")
                            if ref:
                                ref_table = ref.this.this.name
                                ref_cols = [c.name for c in ref.this.expressions]
                                for s, r in zip(src_cols, ref_cols):
                                    fks[s] = f"{ref_table}.{r}"
                                    edges.append((f"{tname}.{s}", f"{ref_table}.{r}"))

            for col in columns:
                col.is_primary_key = col.name in pks
                if col.name in fks:
                    col.is_foreign_key = True
                    col.references = fks[col.name]

            # Real row count from the loaded seed data
            row_count = (
                self._conn.execute(f"SELECT COUNT(*) FROM '{tname}'").fetchone()[0]
                if self._table_exists(tname)
                else 0
            )

            tables.append(TableInfo(name=tname, row_count=row_count, columns=columns))

        return DBProfile(db_name=self.db_name, tables=tables, relationship_edges=edges)

    def _table_exists(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        return row is not None

    # -- read-only execution -----------------------------------------------------

    def execute_read(self, sql: str, limit: int = 200) -> list[dict[str, Any]]:
        self.connect()
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT statements are permitted.")
        # Agents emit MySQL; the engine is SQLite. Transpile at the boundary.
        sql = _mysql_to_sqlite(sql)
        if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            sql = sql.rstrip().rstrip(";") + f" LIMIT {limit}"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def explain(self, sql: str) -> bool:
        """SQLite EXPLAIN QUERY PLAN as the no-execution syntax probe.

        On failure the engine's actual error text is kept in
        `last_explain_error` so the verification layer can report (and the
        regeneration loop can correct) the real problem — e.g.
        "no such column: t.artist_id" — instead of a generic rejection."""
        self.connect()
        self.last_explain_error: str | None = None
        try:
            sql_lite = _mysql_to_sqlite(sql)
            self._conn.execute(f"EXPLAIN QUERY PLAN {sql_lite.rstrip(';')}")
            return True
        except Exception as e:
            self.last_explain_error = str(e)
            return False
