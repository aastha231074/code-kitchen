"""Unit tests that don't need Postgres/Pub/Sub running -- fast enough for
CI on every push. Integration testing against the real stack happens via
`make up && make seed` locally.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("USE_MOCK_AI", "true")

from services.common.ai import _mock_embedding
from services.common.db import to_vector_literal


def test_mock_embedding_is_deterministic():
    a = _mock_embedding("Backend Engineer at Acme", 768)
    b = _mock_embedding("Backend Engineer at Acme", 768)
    assert a == b


def test_mock_embedding_differs_for_different_text():
    a = _mock_embedding("Backend Engineer", 768)
    b = _mock_embedding("Frontend Engineer", 768)
    assert a != b


def test_mock_embedding_has_requested_dimension():
    vec = _mock_embedding("anything", 128)
    assert len(vec) == 128


def test_to_vector_literal_format():
    literal = to_vector_literal([0.1, -0.2, 0.30000001])
    assert literal.startswith("[") and literal.endswith("]")
    assert literal.count(",") == 2


def test_seed_data_fetch_shape():
    from services.ingest_indeed.sources import seed_data

    postings = seed_data.fetch(limit=5, seed=42)
    assert len(postings) == 5
    for p in postings:
        assert {"external_id", "title", "company", "description"}.issubset(p.keys())


def test_seed_data_deterministic_with_seed():
    from services.ingest_indeed.sources import seed_data

    a = seed_data.fetch(limit=5, seed=1)
    b = seed_data.fetch(limit=5, seed=1)
    assert a == b
