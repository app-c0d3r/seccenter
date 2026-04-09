"""Unit tests for n8n dispatcher background task."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.n8n_dispatcher import dispatch_to_n8n


pytestmark = pytest.mark.asyncio


class TestDispatchToN8n:
    """Tests for the dispatch_to_n8n background task."""

    async def test_successful_dispatch(self) -> None:
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=200)
        mock_db_factory = AsyncMock()

        await dispatch_to_n8n(
            http_client=mock_client,
            webhook_url="http://n8n:5678/webhook/enrich",
            payload={"session_id": "s1", "batch_id": "b1", "assets": []},
            batch_id="b1",
            asset_ids=["a1"],
            db_session_factory=mock_db_factory,
        )

        mock_client.post.assert_called_once()

    async def test_failed_dispatch_triggers_compensating_transaction(self) -> None:
        import httpx
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        mock_session = AsyncMock()
        mock_db_factory = MagicMock()
        mock_db_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.n8n_dispatcher.repository") as mock_repo:
            mock_repo.update_batch_status = AsyncMock()
            mock_repo.bulk_revert_assets_to_pending = AsyncMock()

            await dispatch_to_n8n(
                http_client=mock_client,
                webhook_url="http://n8n:5678/webhook/enrich",
                payload={"session_id": "s1", "batch_id": "b1", "assets": []},
                batch_id="b1",
                asset_ids=["a1", "a2"],
                db_session_factory=mock_db_factory,
            )

            mock_repo.update_batch_status.assert_called_once_with(
                mock_session, "b1", "FAILED"
            )
            mock_repo.bulk_revert_assets_to_pending.assert_called_once_with(
                mock_session, ["a1", "a2"]
            )
