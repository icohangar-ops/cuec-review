from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from control_spine import exit_code
from cuec_review.engine import Cuec, CuecStatus, Opinion, SocReport, review
from cuec_review.evidence import evidence_markdown, evidence_pack


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _load(path: Path):
    raw = json.loads(path.read_text())
    reports = tuple(
        SocReport(
            vendor_id=r["vendor_id"],
            vendor_name=r["vendor_name"],
            report_type=r["report_type"],
            period_start=date.fromisoformat(r["period_start"]),
            period_end=date.fromisoformat(r["period_end"]),
            opinion=Opinion(r["opinion"]),
            bridge_letter_through=_d(r.get("bridge_letter_through")),
            exceptions=tuple(r.get("exceptions") or ()),
        )
        for r in raw["reports"]
    )
    cuecs = tuple(
        Cuec(
            cuec_id=c["cuec_id"],
            vendor_id=c["vendor_id"],
            description=c["description"],
            owner=c.get("owner", ""),
            mapped_internal_control=c.get("mapped_internal_control", ""),
            status=CuecStatus(c["status"]),
            evidence_ref=c.get("evidence_ref", ""),
        )
        for c in raw["cuecs"]
    )
    return reports, cuecs, raw


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SOC 1 / CUEC review + evidence pack")
    p.add_argument("register_json")
    p.add_argument("--as-of", required=True)
    p.add_argument("--period-start", required=True)
    p.add_argument("--period-end", required=True)
    p.add_argument("--period-label", default="")
    p.add_argument("--owner", default="")
    args = p.parse_args(argv)
    reports, cuecs, _ = _load(Path(args.register_json))
    result = review(
        reports,
        cuecs,
        date.fromisoformat(args.as_of),
        date.fromisoformat(args.period_start),
        date.fromisoformat(args.period_end),
    )
    label = args.period_label or f"{args.period_start} to {args.period_end}"
    pack = evidence_pack(reports, cuecs, result, label, args.owner)
    print(evidence_markdown(pack))
    print(pack["lock_state"], file=sys.stderr)
    return exit_code(pack)


if __name__ == "__main__":
    raise SystemExit(main())
