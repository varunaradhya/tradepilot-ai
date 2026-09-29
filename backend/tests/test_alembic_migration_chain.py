from __future__ import annotations

import ast
from pathlib import Path


VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _revisions():
    revisions = {}
    for path in sorted(VERSIONS.glob("*.py")):
        if path.name.startswith("__"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    if isinstance(node.value, ast.Constant):
                        values[target.id] = node.value.value
        revisions[path.name] = values
    return revisions


def test_alembic_revisions_are_unique_and_form_one_linear_chain():
    revisions = _revisions()
    ids = [values["revision"] for values in revisions.values()]
    assert len(ids) == 18
    assert len(ids) == len(set(ids))

    by_id = {values["revision"]: values["down_revision"] for values in revisions.values()}
    assert by_id["20260815_0001"] is None

    ordered = sorted(ids)
    for previous, current in zip(ordered, ordered[1:]):
        assert by_id[current] == previous


def test_recent_learning_link_migrations_are_in_chain():
    revisions = _revisions()
    assert revisions["20260929_0013_paper_learning_link.py"]["down_revision"] == "20260928_0012"
    assert revisions["20260929_0014_unique_paper_learning_link.py"]["down_revision"] == "20260929_0013"
    assert revisions["20260929_0015_learning_event_time.py"]["down_revision"] == "20260929_0014"
    assert revisions["20260929_0016_ml_lineage.py"]["down_revision"] == "20260929_0015"
    assert revisions["20260929_0017_holding_uniqueness.py"]["down_revision"] == "20260929_0016"
    assert revisions["20260929_0018_password_changed_at.py"]["down_revision"] == "20260929_0017"


def test_alembic_runtime_fresh_upgrade_and_recovery(tmp_path, monkeypatch):
    import os
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "fresh.db"
    env = os.environ.copy()
    env["TRADEPILOT_DATABASE_URL"] = f"sqlite:///{db_path}"

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    # Fresh database: full migration chain must build successfully.
    run("upgrade", "head")

    # Existing database: a partially upgraded installation must reach head.
    run("downgrade", "20260929_0015")
    run("upgrade", "head")

    # Recovery path: complete downgrade and rebuild must also succeed.
    run("downgrade", "base")
    run("upgrade", "head")

    assert db_path.exists()
