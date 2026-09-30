"""Create a deterministic manifest of strict-valid raw NSE five-minute sessions."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.strict_session_certification import certify_nse_five_minute_session, summarize_certifications


def certify_directory(root: Path) -> dict:
    clean_directory = root / "dhan_equity_clean"
    if not clean_directory.exists():
        raise FileNotFoundError(f"Clean data directory not found: {clean_directory}")
    certifications = []
    for path in sorted(clean_directory.glob("*.jsonl")):
        by_session: dict[str, list[dict]] = defaultdict(list)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            session_date = datetime.fromisoformat(row["timestamp"]).date().isoformat()
            by_session[session_date].append(row)
        for session_date, rows in sorted(by_session.items()):
            certifications.append(
                certify_nse_five_minute_session(
                    symbol=path.stem,
                    session_date=datetime.fromisoformat(session_date).date(),
                    rows=rows,
                    corporate_action_adjusted=None,
                )
            )
    return {
        "schema_version": "1.0",
        "classification_policy": "raw exact 5-minute clock grid; no timestamp transformation",
        "corporate_action_state": "UNKNOWN",
        "sessions": certifications,
        "summary": summarize_certifications(certifications),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = certify_directory(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
