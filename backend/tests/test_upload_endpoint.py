"""
Tests for the upload endpoint and session management.
"""

import pytest
from fastapi import HTTPException
from app.routers.sessions import (
    upload_and_compare,
    list_sessions,
    get_session,
    get_session_summary,
    get_trade,
    update_field_comparison,
    bulk_update,
    _build_export_response,
)
from app.schemas import FieldComparisonUpdate, BulkUpdateRequest


pytestmark = pytest.mark.asyncio


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


async def seed_upload(db, filename: str, content: bytes, emisor_name: str = "", receptor_name: str = ""):
    return await upload_and_compare(
        file=FakeUploadFile(filename, content),
        emisor_name=emisor_name,
        receptor_name=receptor_name,
        db=db,
    )


class TestUploadEndpoint:
    async def test_upload_sample_csv(self, db_session, sample_csv_bytes):
        """Upload sample CSV and verify session creation."""
        session = await seed_upload(
            db_session,
            "sftr_reconciliation_sample.csv",
            sample_csv_bytes,
            emisor_name="Santander",
            receptor_name="Counterparty",
        )
        assert session.total_trades == 5
        assert session.total_fields == 775  # 5 trades × 155 fields
        assert session.total_unmatches == 4
        assert session.critical_count == 2
        assert session.warning_count == 2
        assert session.trades_with_unmatches == 4
        assert session.sft_type == "Repo"
        assert session.action_type == "NEWT"
        assert session.emisor_name == "Santander"
        assert session.receptor_name == "Counterparty"

    async def test_upload_minimal_csv(self, db_session, minimal_csv_bytes):
        """Upload minimal CSV with known mismatch."""
        session = await seed_upload(
            db_session,
            "test.csv",
            minimal_csv_bytes,
            emisor_name="Test",
            receptor_name="Test2",
        )
        assert session.total_trades == 1
        assert session.total_unmatches >= 1  # At least the principal amount mismatch

    async def test_upload_empty_csv(self, db_session):
        """Upload CSV with header only should fail."""
        content = b"UTI;SFT_Type;Action_Type"
        with pytest.raises(Exception) as exc_info:
            await seed_upload(db_session, "empty.csv", content)
        assert "No data rows found in file" in str(exc_info.value)

    async def test_default_emisor_receptor(self, db_session, minimal_csv_bytes):
        """Default names should be CP1/CP2 when not provided."""
        session = await seed_upload(db_session, "test.csv", minimal_csv_bytes)
        assert session.emisor_name == "CP1"
        assert session.receptor_name == "CP2"


class TestSessionEndpoints:
    async def _upload(self, db_session, sample_csv_bytes):
        session = await seed_upload(
            db_session,
            "test.csv",
            sample_csv_bytes,
            emisor_name="Santander",
            receptor_name="CP",
        )
        return {"id": session.id}

    async def test_list_sessions(self, db_session, sample_csv_bytes):
        await self._upload(db_session, sample_csv_bytes)
        data = list_sessions(skip=0, limit=50, db=db_session)
        assert len(data) == 1

    async def test_get_session_detail(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = get_session(session["id"], skip=0, limit=100, has_unmatches=None, search=None, min_severity=None, db=db_session)
        assert len(data.trades) == 5

    async def test_get_session_summary(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = get_session_summary(session["id"], db=db_session)
        assert data.total_trades == 5
        assert data.total_unmatches == 4
        assert data.critical_count == 2

    async def test_filter_trades_with_unmatches(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = get_session(session["id"], skip=0, limit=100, has_unmatches=True, search=None, min_severity=None, db=db_session)
        # Trades 2, 3, 4, 5 have unmatches (Fixed rate in Trade 2 caught by per-field tolerance)
        assert len(data.trades) == 4

    async def test_filter_trades_critical(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = get_session(session["id"], skip=0, limit=100, has_unmatches=None, search=None, min_severity="CRITICAL", db=db_session)
        # Only trades 3 and 4 have critical unmatches
        assert len(data.trades) == 2

    async def test_search_trades_by_uti(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = get_session(session["id"], skip=0, limit=100, has_unmatches=None, search="00003", min_severity=None, db=db_session)
        assert len(data.trades) == 1
        assert "00003" in data.trades[0].uti

    async def test_session_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_session(999, skip=0, limit=100, has_unmatches=None, search=None, min_severity=None, db=db_session)
        assert exc_info.value.status_code == 404


class TestTradeEndpoints:
    async def _upload(self, db_session, sample_csv_bytes):
        session = await seed_upload(db_session, "test.csv", sample_csv_bytes)
        return {"id": session.id}

    async def test_get_trade_detail(self, db_session, sample_csv_bytes):
        await self._upload(db_session, sample_csv_bytes)
        data = get_trade(1, db=db_session)
        assert len(data.field_comparisons) == 155

    async def test_trade_not_found(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            get_trade(999, db=db_session)
        assert exc_info.value.status_code == 404


class TestFieldComparisonEndpoints:
    async def _upload(self, db_session, sample_csv_bytes):
        session = await seed_upload(db_session, "test.csv", sample_csv_bytes)
        return {"id": session.id}

    async def test_update_field_comparison(self, db_session, sample_csv_bytes):
        await self._upload(db_session, sample_csv_bytes)
        # Get trade 3 which has an unmatch
        trade = get_trade(3, db=db_session)
        unmatch = next(fc for fc in trade.field_comparisons if fc.result == "UNMATCH")

        data = update_field_comparison(
            unmatch.id,
            FieldComparisonUpdate(status="RESOLVED", assignee="analyst1", notes="Fixed"),
            db=db_session,
        )
        assert data.status == "RESOLVED"
        assert data.assignee == "analyst1"
        assert data.notes == "Fixed"

    async def test_bulk_resolve(self, db_session, sample_csv_bytes):
        session = await self._upload(db_session, sample_csv_bytes)
        data = bulk_update(
            session["id"],
            BulkUpdateRequest(action="resolve_all"),
            db=db_session,
        )
        assert data["updated"] == 4  # 4 unmatches resolved


class TestExportEndpoint:
    async def test_export_xlsx(self, db_session, sample_csv_bytes):
        session = await seed_upload(db_session, "test.csv", sample_csv_bytes)
        response = _build_export_response(session_id=session.id, db=db_session)
        assert "spreadsheetml" in response.media_type
        assert "attachment; filename=" in response.headers["Content-Disposition"]

    async def test_export_only_unmatches(self, db_session, sample_csv_bytes):
        session = await seed_upload(db_session, "test.csv", sample_csv_bytes)
        response = _build_export_response(session_id=session.id, db=db_session, only_unmatches=True)
        assert "attachment; filename=" in response.headers["Content-Disposition"]
