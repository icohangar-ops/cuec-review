"""SOC 1 / CUEC review engine.

Complementary user-entity controls in a SOC report have to be extracted,
owned, mapped to an internal control, and evidenced for the period the SOC
actually covers. agent-governance does not cover this step.

The engine does not parse a PDF. Extraction is a documented input. The engine
tests whether the register is complete enough to be evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Opinion(str, Enum):
    UNQUALIFIED = "unqualified"
    QUALIFIED = "qualified"
    ADVERSE = "adverse"
    DISCLAIMER = "disclaimer"


class CuecStatus(str, Enum):
    EVIDENCED = "evidenced"
    GAP = "gap"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class SocReport:
    vendor_id: str
    vendor_name: str
    report_type: str  # SOC 1 Type 2, SOC 2 Type 2
    period_start: date
    period_end: date
    opinion: Opinion
    bridge_letter_through: date | None
    exceptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Cuec:
    cuec_id: str
    vendor_id: str
    description: str
    owner: str
    mapped_internal_control: str
    status: CuecStatus
    evidence_ref: str = ""


@dataclass(frozen=True)
class Finding:
    severity: str  # exception | deficiency
    code: str
    message: str
    vendor_id: str
    cuec_id: str | None = None


@dataclass(frozen=True)
class ReviewResult:
    findings: tuple[Finding, ...]
    covered_vendors: int
    open_gaps: int
    expired_reports: int


def _covers(report: SocReport, period_start: date, period_end: date) -> bool:
    covered_end = report.bridge_letter_through or report.period_end
    return report.period_start <= period_start and covered_end >= period_end


def review(
    reports: tuple[SocReport, ...],
    cuecs: tuple[Cuec, ...],
    as_of: date,
    entity_period_start: date,
    entity_period_end: date,
) -> ReviewResult:
    findings: list[Finding] = []
    by_vendor: dict[str, list[SocReport]] = {}
    for r in reports:
        by_vendor.setdefault(r.vendor_id, []).append(r)

    expired = 0
    for vendor_id, vendor_reports in by_vendor.items():
        latest = max(vendor_reports, key=lambda r: r.period_end)
        if not _covers(latest, entity_period_start, entity_period_end):
            expired += 1
            findings.append(
                Finding(
                    "exception",
                    "SOC-EXPIRED",
                    (
                        f"{latest.vendor_name} SOC period ends {latest.period_end.isoformat()} "
                        f"with no bridge letter covering the entity period ending "
                        f"{entity_period_end.isoformat()}"
                    ),
                    vendor_id,
                )
            )
        if latest.opinion != Opinion.UNQUALIFIED:
            findings.append(
                Finding(
                    "exception",
                    "SOC-OPINION",
                    f"{latest.vendor_name} opinion is {latest.opinion.value}",
                    vendor_id,
                )
            )
        for exc in latest.exceptions:
            findings.append(
                Finding("exception", "SOC-EXCEPTION", exc, vendor_id)
            )

    open_gaps = 0
    for c in cuecs:
        if not c.owner:
            open_gaps += 1
            findings.append(
                Finding("deficiency", "CUEC-NO-OWNER", "CUEC has no named owner", c.vendor_id, c.cuec_id)
            )
        if not c.mapped_internal_control:
            open_gaps += 1
            findings.append(
                Finding(
                    "deficiency",
                    "CUEC-UNMAPPED",
                    "CUEC is not mapped to an internal control",
                    c.vendor_id,
                    c.cuec_id,
                )
            )
        if c.status is CuecStatus.GAP:
            open_gaps += 1
            findings.append(
                Finding("deficiency", "CUEC-GAP", "CUEC evidence missing for the period", c.vendor_id, c.cuec_id)
            )
        if c.status is CuecStatus.EVIDENCED and not c.evidence_ref:
            open_gaps += 1
            findings.append(
                Finding(
                    "deficiency",
                    "CUEC-NO-REF",
                    "Marked evidenced but no evidence reference",
                    c.vendor_id,
                    c.cuec_id,
                )
            )

    vendors_with_cuecs = {c.vendor_id for c in cuecs}
    for vendor_id, vendor_reports in by_vendor.items():
        if vendor_id not in vendors_with_cuecs:
            findings.append(
                Finding(
                    "deficiency",
                    "CUEC-NONE-EXTRACTED",
                    f"{vendor_reports[0].vendor_name}: SOC on file, no CUECs extracted",
                    vendor_id,
                )
            )
            open_gaps += 1

    return ReviewResult(
        findings=tuple(findings),
        covered_vendors=len(by_vendor),
        open_gaps=open_gaps,
        expired_reports=expired,
    )
