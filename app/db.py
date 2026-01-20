"""数据库连接与会话管理。"""

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    """SQLAlchemy 基类。"""

    pass


# SQLite 需要 ``check_same_thread=False`` 以支持多线程；其他数据库可忽略
engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """提供事务范围的 Session 上下文管理器。"""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入函数，提供数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_assignments_schema(db_engine: Engine) -> None:
    """为旧版 SQLite assignments 表补齐 v2 所需字段。"""
    if db_engine.url.drivername != "sqlite":
        return

    with db_engine.begin() as conn:
        def maybe_rebuild_assignments() -> None:
            cols = conn.execute(text("PRAGMA table_info(assignments)")).fetchall()
            if not cols:
                return
            col_names = {row[1] for row in cols}
            if "milestones_json" not in col_names:
                return

            def col_expr(name: str, fallback: str) -> str:
                return name if name in col_names else fallback

            conn.execute(text("ALTER TABLE assignments RENAME TO assignments_old"))
            conn.execute(
                text(
                    """
                    CREATE TABLE assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(255) NOT NULL,
                        topic VARCHAR(255) NOT NULL,
                        description TEXT,
                        school_stage VARCHAR(7) NOT NULL,
                        grade INTEGER NOT NULL,
                        main_subject_id INTEGER NOT NULL,
                        related_subject_ids JSON NOT NULL,
                        assignment_type VARCHAR(9) NOT NULL,
                        practical_subtype VARCHAR(11),
                        inquiry_subtype VARCHAR(10),
                        inquiry_depth VARCHAR(12) NOT NULL,
                        submission_mode VARCHAR(6) NOT NULL,
                        duration_weeks INTEGER NOT NULL,
                        deadline DATETIME,
                        objectives_json JSON NOT NULL,
                        phases_json JSON NOT NULL,
                        rubric_json JSON NOT NULL,
                        created_by INTEGER NOT NULL,
                        document_id INTEGER,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        is_published BOOLEAN NOT NULL,
                        published_at DATETIME,
                        FOREIGN KEY(main_subject_id) REFERENCES subjects (id),
                        FOREIGN KEY(created_by) REFERENCES users (id),
                        FOREIGN KEY(document_id) REFERENCES documents (id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO assignments (
                        id,
                        title,
                        topic,
                        description,
                        school_stage,
                        grade,
                        main_subject_id,
                        related_subject_ids,
                        assignment_type,
                        practical_subtype,
                        inquiry_subtype,
                        inquiry_depth,
                        submission_mode,
                        duration_weeks,
                        deadline,
                        objectives_json,
                        phases_json,
                        rubric_json,
                        created_by,
                        document_id,
                        created_at,
                        updated_at,
                        is_published,
                        published_at
                    )
                    SELECT
                        id,
                        {col_expr("title", "''")},
                        {col_expr("topic", "''")},
                        {col_expr("description", "NULL")},
                        {col_expr("school_stage", "'PRIMARY'")},
                        {col_expr("grade", "1")},
                        {col_expr("main_subject_id", "1")},
                        COALESCE({col_expr("related_subject_ids", "NULL")}, '[]'),
                        {col_expr("assignment_type", "'INQUIRY'")},
                        {col_expr("practical_subtype", "NULL")},
                        {col_expr("inquiry_subtype", "NULL")},
                        {col_expr("inquiry_depth", "'INTERMEDIATE'")},
                        {col_expr("submission_mode", "'PHASED'")},
                        {col_expr("duration_weeks", "2")},
                        {col_expr("deadline", "NULL")},
                        COALESCE({col_expr("objectives_json", "NULL")}, '{{}}'),
                        COALESCE({col_expr("phases_json", "NULL")}, '[]'),
                        COALESCE({col_expr("rubric_json", "NULL")}, '{{}}'),
                        {col_expr("created_by", "1")},
                        {col_expr("document_id", "NULL")},
                        COALESCE({col_expr("created_at", "NULL")}, CURRENT_TIMESTAMP),
                        COALESCE({col_expr("updated_at", "NULL")}, CURRENT_TIMESTAMP),
                        COALESCE({col_expr("is_published", "NULL")}, 0),
                        {col_expr("published_at", "NULL")}
                    FROM assignments_old
                    """
                )
            )
            conn.execute(text("DROP TABLE assignments_old"))

        def maybe_rebuild_submissions() -> None:
            cols = conn.execute(text("PRAGMA table_info(submissions)")).fetchall()
            if not cols:
                return
            col_names = {row[1] for row in cols}
            col_by_name = {row[1]: row for row in cols}
            group_notnull = col_by_name.get("group_id", [None, None, None, 0])[3] == 1
            submitted_notnull = col_by_name.get("submitted_at", [None, None, None, 0])[3] == 1
            if "milestone_index" not in col_names and not group_notnull and not submitted_notnull:
                return

            phase_expr = "phase_index" if "phase_index" in col_names else "milestone_index"
            group_expr = "NULLIF(group_id, 0)" if "group_id" in col_names else "NULL"
            step_expr = "step_index" if "step_index" in col_names else "NULL"
            status_expr = "UPPER(status)" if "status" in col_names else "'DRAFT'"
            content_expr = "COALESCE(content_json, '{}')" if "content_json" in col_names else "'{}'"
            attachments_expr = "COALESCE(attachments_json, '[]')" if "attachments_json" in col_names else "'[]'"
            checkpoints_expr = "COALESCE(checkpoints_json, '{}')" if "checkpoints_json" in col_names else "'{}'"
            created_expr = "COALESCE(created_at, CURRENT_TIMESTAMP)" if "created_at" in col_names else "CURRENT_TIMESTAMP"
            submitted_expr = "submitted_at" if "submitted_at" in col_names else "NULL"
            updated_expr = "COALESCE(updated_at, CURRENT_TIMESTAMP)" if "updated_at" in col_names else "CURRENT_TIMESTAMP"
            student_expr = "COALESCE(student_id, 1)" if "student_id" in col_names else "1"

            conn.execute(text("ALTER TABLE submissions RENAME TO submissions_old"))
            conn.execute(
                text(
                    """
                    CREATE TABLE submissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        assignment_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        group_id INTEGER,
                        phase_index INTEGER,
                        step_index INTEGER,
                        status VARCHAR(50),
                        content_json JSON,
                        attachments_json JSON,
                        checkpoints_json JSON,
                        created_at DATETIME,
                        submitted_at DATETIME,
                        updated_at DATETIME,
                        FOREIGN KEY(assignment_id) REFERENCES assignments (id) ON DELETE CASCADE,
                        FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE,
                        FOREIGN KEY(group_id) REFERENCES project_groups (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO submissions (
                        id, assignment_id, student_id, group_id, phase_index, step_index,
                        status, content_json, attachments_json, checkpoints_json,
                        created_at, submitted_at, updated_at
                    )
                    SELECT
                        id,
                        assignment_id,
                        {student_expr},
                        {group_expr},
                        COALESCE({phase_expr}, 0),
                        {step_expr},
                        {status_expr},
                        {content_expr},
                        {attachments_expr},
                        {checkpoints_expr},
                        {created_expr},
                        {submitted_expr},
                        {updated_expr}
                    FROM submissions_old
                    """
                )
            )
            conn.execute(text("DROP TABLE submissions_old"))

        def ensure_table(
            table: str,
            column_defs: dict[str, str],
            updates: list[str] | None = None,
        ) -> None:
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table},
            ).fetchone()
            if not exists:
                return

            cols = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            }

            for name, definition in column_defs.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
                    cols.add(name)

            if updates:
                for stmt in updates:
                    conn.execute(text(stmt))

        maybe_rebuild_assignments()

        ensure_table(
            "assignments",
            {
                "topic": "VARCHAR(255)",
                "description": "TEXT",
                "school_stage": "VARCHAR(50)",
                "grade": "INTEGER",
                "main_subject_id": "INTEGER",
                "related_subject_ids": "JSON",
                "assignment_type": "VARCHAR(50)",
                "practical_subtype": "VARCHAR(50)",
                "inquiry_subtype": "VARCHAR(50)",
                "inquiry_depth": "VARCHAR(50)",
                "submission_mode": "VARCHAR(50)",
                "duration_weeks": "INTEGER",
                "deadline": "DATETIME",
                "objectives_json": "JSON",
                "phases_json": "JSON",
                "created_by": "INTEGER",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "is_published": "BOOLEAN",
                "published_at": "DATETIME",
            },
            updates=[
                "UPDATE assignments SET school_stage = COALESCE(school_stage, 'PRIMARY')",
                "UPDATE assignments SET grade = COALESCE(grade, 1)",
                "UPDATE assignments SET main_subject_id = COALESCE(main_subject_id, 1)",
                "UPDATE assignments SET related_subject_ids = COALESCE(related_subject_ids, '[]')",
                "UPDATE assignments SET assignment_type = COALESCE(assignment_type, 'INQUIRY')",
                "UPDATE assignments SET inquiry_depth = COALESCE(inquiry_depth, 'INTERMEDIATE')",
                "UPDATE assignments SET submission_mode = COALESCE(submission_mode, 'PHASED')",
                "UPDATE assignments SET duration_weeks = COALESCE(duration_weeks, 2)",
                "UPDATE assignments SET objectives_json = COALESCE(objectives_json, '{}')",
                "UPDATE assignments SET phases_json = COALESCE(phases_json, '[]')",
                "UPDATE assignments SET created_by = COALESCE(created_by, 1)",
                "UPDATE assignments SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
                "UPDATE assignments SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)",
                "UPDATE assignments SET is_published = COALESCE(is_published, 0)",
                "UPDATE assignments SET school_stage = UPPER(school_stage)",
                "UPDATE assignments SET assignment_type = UPPER(assignment_type)",
                "UPDATE assignments SET inquiry_depth = UPPER(inquiry_depth)",
                "UPDATE assignments SET submission_mode = UPPER(submission_mode)",
                "UPDATE assignments SET practical_subtype = UPPER(practical_subtype) WHERE practical_subtype IS NOT NULL",
                "UPDATE assignments SET inquiry_subtype = UPPER(inquiry_subtype) WHERE inquiry_subtype IS NOT NULL",
            ],
        )
        conn.execute(
            text(
                "UPDATE assignments SET topic = COALESCE(NULLIF(topic, ''), title, '未设置') "
                "WHERE (topic IS NULL OR topic = '')"
            )
        )

        ensure_table(
            "project_groups",
            {"created_at": "DATETIME"},
            updates=[
                "UPDATE project_groups SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
            ],
        )

        maybe_rebuild_submissions()

        ensure_table(
            "submissions",
            {
                "student_id": "INTEGER",
                "phase_index": "INTEGER",
                "step_index": "INTEGER",
                "status": "VARCHAR(50)",
                "content_json": "JSON",
                "attachments_json": "JSON",
                "checkpoints_json": "JSON",
                "created_at": "DATETIME",
                "submitted_at": "DATETIME",
                "updated_at": "DATETIME",
            },
            updates=[
                "UPDATE submissions SET student_id = COALESCE(student_id, 1)",
                "UPDATE submissions SET phase_index = COALESCE(phase_index, 0)",
                "UPDATE submissions SET status = COALESCE(status, 'DRAFT')",
                "UPDATE submissions SET content_json = COALESCE(content_json, '{}')",
                "UPDATE submissions SET attachments_json = COALESCE(attachments_json, '[]')",
                "UPDATE submissions SET checkpoints_json = COALESCE(checkpoints_json, '{}')",
                "UPDATE submissions SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
                "UPDATE submissions SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)",
                "UPDATE submissions SET status = UPPER(status)",
            ],
        )

        ensure_table(
            "evaluations",
            {},
            updates=[
                "UPDATE evaluations SET evaluation_type = UPPER(evaluation_type)",
            ],
        )

        ensure_table(
            "documents",
            {"source": "VARCHAR(20)"},
            updates=[
                "UPDATE documents SET source = COALESCE(source, 'user')",
                "UPDATE documents SET source = 'system' WHERE filename LIKE 'W0%.docx'",
                "UPDATE documents SET source = 'system' WHERE filename LIKE '00_%' OR filename LIKE '01_%' OR filename LIKE '02_%' OR filename LIKE '03_%' OR filename LIKE '04_%' OR filename LIKE '05_%' OR filename LIKE '06_%' OR filename LIKE '07_%' OR filename LIKE '08_%' OR filename LIKE '09_%' OR filename LIKE '10_%' OR filename LIKE '11_%' OR filename LIKE '12_%' OR filename LIKE '13_%' OR filename LIKE '14_%'",
            ],
        )
