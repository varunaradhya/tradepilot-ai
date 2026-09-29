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
    assert len(ids) == 14
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
