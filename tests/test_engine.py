from datetime import date

from cuec_review.engine import Cuec, CuecStatus, Opinion, SocReport, review
from cuec_review.evidence import evidence_pack


def _payroll_soc(**kwargs) -> SocReport:
    defaults = dict(
        vendor_id="ADP",
        vendor_name="ADP",
        report_type="SOC 1 Type 2",
        period_start=date(2025, 7, 1),
        period_end=date(2026, 6, 30),
        opinion=Opinion.UNQUALIFIED,
        bridge_letter_through=None,
        exceptions=(),
    )
    defaults.update(kwargs)
    return SocReport(**defaults)


def test_clean_register_has_no_findings() -> None:
    reports = (_payroll_soc(),)
    cuecs = (
        Cuec(
            "CUEC-1",
            "ADP",
            "User entity reviews payroll change reports",
            owner="Controller",
            mapped_internal_control="IC-PAY-04",
            status=CuecStatus.EVIDENCED,
            evidence_ref="workpaper/2026-06-payroll-changes.pdf",
        ),
    )
    result = review(reports, cuecs, date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    assert result.open_gaps == 0
    assert result.expired_reports == 0
    assert result.findings == ()


def test_expired_soc_without_bridge_letter() -> None:
    reports = (_payroll_soc(period_end=date(2025, 12, 31)),)
    cuecs = (
        Cuec(
            "CUEC-1",
            "ADP",
            "review changes",
            owner="Controller",
            mapped_internal_control="IC-PAY-04",
            status=CuecStatus.EVIDENCED,
            evidence_ref="wp-1",
        ),
    )
    result = review(reports, cuecs, date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    assert result.expired_reports == 1
    assert any(f.code == "SOC-EXPIRED" for f in result.findings)


def test_bridge_letter_extends_coverage() -> None:
    reports = (
        _payroll_soc(
            period_end=date(2025, 12, 31),
            bridge_letter_through=date(2026, 6, 30),
        ),
    )
    cuecs = (
        Cuec(
            "CUEC-1",
            "ADP",
            "review changes",
            owner="Controller",
            mapped_internal_control="IC-PAY-04",
            status=CuecStatus.EVIDENCED,
            evidence_ref="wp-1",
        ),
    )
    result = review(reports, cuecs, date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    assert result.expired_reports == 0


def test_unmapped_and_unowned_cuec() -> None:
    reports = (_payroll_soc(),)
    cuecs = (
        Cuec("CUEC-1", "ADP", "access reviews", owner="", mapped_internal_control="", status=CuecStatus.GAP),
    )
    result = review(reports, cuecs, date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    codes = {f.code for f in result.findings}
    assert {"CUEC-NO-OWNER", "CUEC-UNMAPPED", "CUEC-GAP"} <= codes
    assert result.open_gaps >= 3


def test_soc_with_no_cuecs_extracted() -> None:
    reports = (_payroll_soc(),)
    result = review(reports, (), date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    assert any(f.code == "CUEC-NONE-EXTRACTED" for f in result.findings)


def test_evidence_pack_is_unsigned_until_owner_set() -> None:
    reports = (_payroll_soc(),)
    result = review(reports, (), date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    pack = evidence_pack(reports, (), result, "H1 2026", "")
    assert pack["owner_signoff"] == ""
    assert pack["control_id"] == "ICFR-CUEC-01"
    assert pack["lock_state"] == "EXPLORING"
    assert pack["is_evidence"] is False


def test_signed_clean_pack_locks() -> None:
    reports = (_payroll_soc(),)
    cuecs = (
        Cuec(
            "CUEC-1",
            "ADP",
            "User entity reviews payroll change reports",
            owner="Controller",
            mapped_internal_control="IC-PAY-04",
            status=CuecStatus.EVIDENCED,
            evidence_ref="workpaper/2026-06-payroll-changes.pdf",
        ),
    )
    result = review(reports, cuecs, date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    pack = evidence_pack(reports, cuecs, result, "H1 2026", "Controller")
    assert pack["lock_state"] == "LOCKED"
    assert pack["is_evidence"] is True


def test_signed_gaps_cap_at_provisional() -> None:
    reports = (_payroll_soc(),)
    result = review(reports, (), date(2026, 6, 30), date(2026, 1, 1), date(2026, 6, 30))
    pack = evidence_pack(reports, (), result, "H1 2026", "Controller")
    assert pack["lock_state"] == "PROVISIONAL_LOCK"
    assert pack["is_evidence"] is False
