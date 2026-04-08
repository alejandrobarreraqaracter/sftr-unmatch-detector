"""
Tests for the upload endpoint and session management.
"""

import os
import pytest
from fastapi.testclient import TestClient


class TestUploadEndpoint:
    def test_upload_sample_csv(self, client, sample_csv_path):
        """Upload sample CSV and verify session creation."""
        with open(sample_csv_path, "rb") as f:
            response = client.post(
                "/api/sessions/upload",
                files={"file": ("sftr_reconciliation_sample.csv", f, "text/csv")},
                data={"emisor_name": "Santander", "receptor_name": "Counterparty"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 5
        assert data["total_fields"] == 775  # 5 trades × 155 fields
        assert data["total_unmatches"] == 4
        assert data["critical_count"] == 2
        assert data["warning_count"] == 2
        assert data["trades_with_unmatches"] == 4
        assert data["sft_type"] == "Repo"
        assert data["action_type"] == "NEWT"
        assert data["emisor_name"] == "Santander"
        assert data["receptor_name"] == "Counterparty"

    def test_upload_minimal_csv(self, client, minimal_csv_bytes):
        """Upload minimal CSV with known mismatch."""
        response = client.post(
            "/api/sessions/upload",
            files={"file": ("test.csv", minimal_csv_bytes, "text/csv")},
            data={"emisor_name": "Test", "receptor_name": "Test2"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 1
        assert data["total_unmatches"] >= 1  # At least the principal amount mismatch

    def test_upload_empty_csv(self, client):
        """Upload CSV with header only should fail."""
        content = b"UTI;SFT_Type;Action_Type"
        response = client.post(
            "/api/sessions/upload",
            files={"file": ("empty.csv", content, "text/csv")},
            data={"emisor_name": "A", "receptor_name": "B"},
        )
        assert response.status_code == 400

    def test_default_emisor_receptor(self, client, minimal_csv_bytes):
        """Default names should be CP1/CP2 when not provided."""
        response = client.post(
            "/api/sessions/upload",
            files={"file": ("test.csv", minimal_csv_bytes, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["emisor_name"] == "CP1"
        assert data["receptor_name"] == "CP2"


class TestSessionEndpoints:
    def _upload(self, client, sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            return client.post(
                "/api/sessions/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"emisor_name": "Santander", "receptor_name": "CP"},
            ).json()

    def test_list_sessions(self, client, sample_csv_path):
        self._upload(client, sample_csv_path)
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_session_detail(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get(f"/api/sessions/{session['id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 5

    def test_get_session_summary(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get(f"/api/sessions/{session['id']}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 5
        assert data["total_unmatches"] == 4
        assert data["critical_count"] == 2

    def test_filter_trades_with_unmatches(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get(f"/api/sessions/{session['id']}?has_unmatches=true")
        assert response.status_code == 200
        data = response.json()
        # Trades 2, 3, 4, 5 have unmatches (Fixed rate in Trade 2 caught by per-field tolerance)
        assert len(data["trades"]) == 4

    def test_filter_trades_critical(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get(f"/api/sessions/{session['id']}?min_severity=CRITICAL")
        assert response.status_code == 200
        data = response.json()
        # Only trades 3 and 4 have critical unmatches
        assert len(data["trades"]) == 2

    def test_search_trades_by_uti(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get(f"/api/sessions/{session['id']}?search=00003")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 1
        assert "00003" in data["trades"][0]["uti"]

    def test_session_not_found(self, client):
        response = client.get("/api/sessions/999")
        assert response.status_code == 404


class TestTradeEndpoints:
    def _upload(self, client, sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            return client.post(
                "/api/sessions/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"emisor_name": "A", "receptor_name": "B"},
            ).json()

    def test_get_trade_detail(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.get("/api/trades/1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["field_comparisons"]) == 155

    def test_trade_not_found(self, client):
        response = client.get("/api/trades/999")
        assert response.status_code == 404


class TestFieldComparisonEndpoints:
    def _upload(self, client, sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            return client.post(
                "/api/sessions/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"emisor_name": "A", "receptor_name": "B"},
            ).json()

    def test_update_field_comparison(self, client, sample_csv_path):
        self._upload(client, sample_csv_path)
        # Get trade 3 which has an unmatch
        trade = client.get("/api/trades/3").json()
        unmatch = next(fc for fc in trade["field_comparisons"] if fc["result"] == "UNMATCH")

        response = client.patch(
            f"/api/field-comparisons/{unmatch['id']}",
            json={"status": "RESOLVED", "assignee": "analyst1", "notes": "Fixed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["assignee"] == "analyst1"
        assert data["notes"] == "Fixed"

    def test_bulk_resolve(self, client, sample_csv_path):
        session = self._upload(client, sample_csv_path)
        response = client.post(
            f"/api/sessions/{session['id']}/bulk-update",
            json={"action": "resolve_all"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 4  # 4 unmatches resolved


class TestExportEndpoint:
    def test_export_xlsx(self, client, sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            session = client.post(
                "/api/sessions/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"emisor_name": "A", "receptor_name": "B"},
            ).json()

        response = client.get(f"/api/sessions/{session['id']}/export")
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        assert len(response.content) > 0

    def test_export_only_unmatches(self, client, sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            session = client.post(
                "/api/sessions/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"emisor_name": "A", "receptor_name": "B"},
            ).json()

        response = client.get(f"/api/sessions/{session['id']}/export?only_unmatches=true")
        assert response.status_code == 200
        assert len(response.content) > 0
