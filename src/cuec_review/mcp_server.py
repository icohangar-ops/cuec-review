"""MCP server for the cuec-review engine.

Exposes deterministic SOC 1 / CUEC register review as Model Context Protocol
tools. Thin wrapper — all review logic lives in ``cuec_review.engine`` and
``cuec_review.evidence`` and is reused verbatim; nothing here touches the
network, and SOC report text stays a documented input (the engine does not
parse PDFs).

Follows the same publishing path proven by invoice-audit-engine /
codesentinel: namespace ``io.github.Cubiczan``, stdio transport, published
via the ``mcp-publisher`` CLI.

Run it:

    uvx --from 'cuec-review[mcp]' cuec-review-mcp
    # or, from a checkout:
    uv run --with 'mcp>=1.2,<2' --with . python -m cuec_review.mcp_server
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from cuec_review.engine import Cuec, CuecStatus, Opinion, SocReport, review
from cuec_review.evidence import evidence_pack

mcp = FastMCP(
    "cuec-review",
    instructions=(
        "Deterministic SOC 1 / CUEC register review. Supply the vendor SOC "
        "reports and the CUEC register; the tools check period coverage and "
        "bridge letters, flag unowned / unmapped / unevidenced CUECs, and "
        "render the evidence pack a tester can reperform. SOC text is an "
        "input — the engine does not parse PDFs."
    ),
)


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _register_from_dict(raw: dict[str, Any]) -> tuple[tuple[SocReport, ...], tuple[Cuec, ...]]:
    """Build the register from the CLI/JSON shape (same keys as the CLI's input file)."""
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
    return reports, cuecs


def _jsonify(value: Any) -> Any:
    """JSON-safe conversion (dates become ISO strings)."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


@mcp.tool()
def review_register(
    register: dict[str, Any],
    as_of: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Review one vendor SOC/CUEC register for completeness (findings, gaps, expiry).

    Returns the findings (SOC-EXPIRED / SOC-OPINION / SOC-EXCEPTION /
    CUEC-* deficiencies), covered vendor count, open gap count, and expired
    report count.

    Args:
        register: Expected keys mirror the CLI input file: reports (vendor
            SOC reports) and cuecs (complementary user-entity controls).
        as_of: ISO date of the review.
        period_start: ISO date the entity reporting period starts.
        period_end: ISO date the entity reporting period ends.
    """
    reports, cuecs = _register_from_dict(register)
    result = review(reports, cuecs, date.fromisoformat(as_of),
                    date.fromisoformat(period_start), date.fromisoformat(period_end))
    return _jsonify(asdict(result))


@mcp.tool()
def cuec_evidence_pack(
    register: dict[str, Any],
    as_of: str,
    period_start: str,
    period_end: str,
    period_label: str = "",
) -> dict[str, Any]:
    """Build the SOC/CUEC evidence pack a tester can reperform without the source code.

    Runs the review and renders the control-spine pack (findings, open
    gaps, CUEC register, owner sign-off). Unsigned packs stay EXPLORING;
    open findings are blocking and cannot reach LOCKED.

    Args:
        register: Same shape as review_register's input.
        as_of: ISO date of the review.
        period_start: ISO date the entity reporting period starts.
        period_end: ISO date the entity reporting period ends.
        period_label: Close period label; defaults to "<start> to <end>".
        Sign-off: MCP never accepts an owner — packs built here are always
        unsigned (EXPLORING, not evidence). A named human signs via the CLI
        (--owner), never through MCP.
    """
    reports, cuecs = _register_from_dict(register)
    result = review(reports, cuecs, date.fromisoformat(as_of),
                    date.fromisoformat(period_start), date.fromisoformat(period_end))
    label = period_label or f"{period_start} to {period_end}"
    pack = evidence_pack(reports, cuecs, result, label, "", invoked_via="mcp")
    return _jsonify(pack)


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
