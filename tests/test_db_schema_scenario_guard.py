from sqlalchemy import create_engine, text

from app.db import ensure_sqlite_assignments_schema


def test_assignments_schema_handles_missing_scenario():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE assignments ("
                "id INTEGER PRIMARY KEY, "
                "title TEXT, "
                "topic TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO assignments (id, title, topic) "
                "VALUES (1, 'Title', NULL)"
            )
        )

    try:
        ensure_sqlite_assignments_schema(engine)
    except Exception as exc:
        raise AssertionError(f"schema update should not fail: {exc}") from exc

    with engine.begin() as conn:
        topic = conn.execute(
            text("SELECT topic FROM assignments WHERE id = 1")
        ).scalar_one()

    assert topic == "Title"
