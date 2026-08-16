from __future__ import annotations

from control_spine import Finding, render_spine, seal
from cuec_review.engine import Cuec, ReviewResult, SocReport

FOUNDATION = (
    "SOC report text is an input. This engine does not parse PDFs.",
    "Coverage requires the SOC period plus any bridge letter to span the whole entity reporting period.",
    "A CUEC marked evidenced without a workpaper reference is a gap.",
)

ENGINE_ID = "cuec-review-engine"
ENGINE_VERSION = "0.1.0"


def evidence_pack(
    reports: tuple[SocReport, ...],
    cuecs: tuple[Cuec, ...],
    result: ReviewResult,
    period_label: str,
    owner: str,
) -> dict:
    pack = {
        "control_id": "ICFR-CUEC-01",
        "control_objective": "Service-org SOC reports cover the period; CUECs are owned, mapped, and evidenced.",
        "period": period_label,
        "population_count": len(reports),
        "threshold": "100% of in-scope service orgs; every CUEC has an owner, mapped control, and period evidence or a documented N/A.",
        "covered_vendors": result.covered_vendors,
        "open_gaps": result.open_gaps,
        "expired_reports": result.expired_reports,
        "findings": [
            {
                "severity": f.severity,
                "code": f.code,
                "message": f.message,
                "vendor_id": f.vendor_id,
                "cuec_id": f.cuec_id,
            }
            for f in result.findings
        ],
        "cuec_register": [
            {
                "cuec_id": c.cuec_id,
                "vendor_id": c.vendor_id,
                "owner": c.owner,
                "mapped_internal_control": c.mapped_internal_control,
                "status": c.status.value,
                "evidence_ref": c.evidence_ref,
            }
            for c in cuecs
        ],
        "expiry_calendar": [
            {
                "vendor_id": r.vendor_id,
                "vendor_name": r.vendor_name,
                "period_end": r.period_end.isoformat(),
                "bridge_letter_through": r.bridge_letter_through.isoformat()
                if r.bridge_letter_through
                else None,
            }
            for r in reports
        ],
        "prepared_by": ENGINE_ID,
        "owner_signoff": owner,
        "conclusion": (
            "No open gaps."
            if result.open_gaps == 0 and result.expired_reports == 0
            else f"{result.open_gaps} CUEC gaps, {result.expired_reports} coverage gaps. Not evidence until cleared."
        ),
    }
    blocking = tuple(
        Finding(f.code, f.message, blocking=True) for f in result.findings
    )
    return seal(
        pack,
        engine_id=ENGINE_ID,
        engine_version=ENGINE_VERSION,
        inputs={
            "vendors": [r.vendor_id for r in reports],
            "cuecs": [c.cuec_id for c in cuecs],
            "period": period_label,
        },
        foundation=FOUNDATION,
        blocking_findings=blocking,
    )


def evidence_markdown(pack: dict) -> str:
    lines = [
        f"# CUEC review pack — {pack['period']}",
        "",
        *render_spine(pack),
        f"**Control:** {pack['control_id']}",
        f"**Vendors:** {pack['covered_vendors']}  **Open gaps:** {pack['open_gaps']}  **Expired SOC:** {pack['expired_reports']}",
        f"**Owner sign-off:** {pack['owner_signoff'] or '_unsigned_'}",
        "",
        "## Expiry calendar",
        "",
        "| Vendor | SOC period end | Bridge through |",
        "|---|---|---|",
    ]
    for row in pack["expiry_calendar"]:
        lines.append(
            f"| {row['vendor_name']} | {row['period_end']} | {row['bridge_letter_through'] or '—'} |"
        )
    lines += ["", "## Findings", ""]
    if not pack["findings"]:
        lines.append("None.")
    else:
        for f in pack["findings"]:
            lines.append(f"- **{f['code']}** ({f['severity']}): {f['message']}")
    lines += ["", "## Conclusion", "", pack["conclusion"], ""]
    return "\n".join(lines)
