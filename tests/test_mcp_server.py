"""The MCP server registers the engine's deterministic review as callable tools.

Pins the test suite's clean-register case (covered vendor, zero open gaps,
zero findings) and the expired-SOC exception through the MCP tool path.
Skipped cleanly when the optional ``mcp`` SDK is not installed.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp")

from cuec_review import mcp_server  # noqa: E402


def _tool_names() -> set[str]:
    tools = asyncio.run(mcp_server.mcp.list_tools())
    return {t.name for t in tools}


def _register() -> dict:
    return {
        "reports": [
            {
                "vendor_id": "ADP",
                "vendor_name": "ADP",
                "report_type": "SOC 1 Type 2",
                "period_start": "2025-07-01",
                "period_end": "2026-06-30",
                "opinion": "unqualified",
            }
        ],
        "cuecs": [
            {
                "cuec_id": "CUEC-1",
                "vendor_id": "ADP",
                "description": "User entity reviews payroll change reports",
                "owner": "Controller",
                "mapped_internal_control": "IC-PAY-04",
                "status": "evidenced",
                "evidence_ref": "workpaper/2026-06-payroll-changes.pdf",
            }
        ],
    }


_ARGS = {"as_of": "2026-06-30", "period_start": "2026-01-01", "period_end": "2026-06-30"}


def test_expected_tools_registered() -> None:
    assert _tool_names() >= {"review_register", "cuec_evidence_pack"}


def test_clean_register_has_no_findings_via_mcp() -> None:
    result = mcp_server.review_register(_register(), **_ARGS)
    assert result["open_gaps"] == 0
    assert result["expired_reports"] == 0
    assert result["findings"] == []


def test_expired_soc_surfaces_the_exception_via_mcp() -> None:
    stale = _register()
    stale["reports"][0]["period_end"] = "2025-12-31"
    result = mcp_server.review_register(stale, **_ARGS)
    codes = {f["code"] for f in result["findings"]}
    assert "SOC-EXPIRED" in codes


def test_evidence_pack_pins_population() -> None:
    pack = mcp_server.cuec_evidence_pack(
        _register(), **_ARGS, period_label="H1 2026", owner="Controller"
    )
    assert pack["population_count"] == 1
    assert pack["open_gaps"] == 0
