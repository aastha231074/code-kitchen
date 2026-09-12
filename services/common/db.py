"""Thin Postgres helper shared by every service.

Uses psycopg (v3) with a simple connection-per-call pool. Good enough for a
lab/demo; swap for a real pool (e.g. psycopg_pool) before production load.
"""
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import settings


@contextmanager
def get_conn():
    conn = psycopg.connect(settings.database_url, row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def execute(query: str, params: tuple = ()) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)


def to_vector_literal(vec: list[float]) -> str:
    """pgvector's text input format is '[0.1,0.2,...]', not psycopg's default
    array literal -- format explicitly rather than relying on adaptation.
    """
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"
