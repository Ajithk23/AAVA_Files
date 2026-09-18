from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from utils.db_client import PostgresClient


def get_chat_thread_by_id(
    client: PostgresClient,
    thread_id: str | UUID,
    table_name: str = "docu_chat_userchatthread",
) -> dict[str, Any] | None:
    query = sql.SQL("SELECT * FROM {table} WHERE id = %s").format(
        table=sql.Identifier(table_name)
    )
    with client.connection() as conn, conn.cursor() as cur:
        cur.execute(query, (str(thread_id),))
        row = cur.fetchone()
    return dict(row) if row else None