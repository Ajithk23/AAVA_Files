from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str = "require"

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "PostgresConfig":
        db_settings = settings.get("db") or {}
        required_fields = ("host", "port", "database", "user", "password")
        missing = [field for field in required_fields if not db_settings.get(field)]
        if missing:
            raise ValueError(
                "Database configuration is incomplete. Missing: "
                + ", ".join(missing)
                + ". Set PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD or add a db block to config.yaml."
            )
        return cls(
            host=str(db_settings["host"]),
            port=int(db_settings["port"]),
            database=str(db_settings["database"]),
            user=str(db_settings["user"]),
            password=str(db_settings["password"]),
            sslmode=str(db_settings.get("sslmode", "require")),
        )


class PostgresClient:
    def __init__(self, config: PostgresConfig) -> None:
        self.config = config

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "PostgresClient":
        return cls(PostgresConfig.from_settings(settings))

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        conn = psycopg.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.database,
            user=self.config.user,
            password=self.config.password,
            sslmode=self.config.sslmode,
            row_factory=dict_row,
        )
        try:
            yield conn
        finally:
            conn.close()

    def fetch_one(
        self,
        query: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return dict(row) if row else None

    def fetch_all(
        self,
        query: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    def execute_scalar(
        self,
        query: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> Any:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        if row is None:
            return None
        return next(iter(row.values()))