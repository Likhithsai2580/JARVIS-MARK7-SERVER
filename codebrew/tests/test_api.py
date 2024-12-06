import pytest
from fastapi import status
from datetime import datetime, timedelta
import json

pytestmark = pytest.mark.asyncio

class TestAPI:
    """Test suite for CodeBrew API."""

    @pytest.mark.api
    async def test_health_check(self, test_client, mock_env):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["instance_id"] == int(mock_env["INSTANCE_ID"])
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["busy"], bool)
        assert isinstance(data["active_instances"], int)
        assert isinstance(data["cache_size"], int)
        assert isinstance(data["uptime"], float)

    @pytest.mark.api
    async def test_query_endpoint_success(self, test_client, api_key, test_prompt):
        """Test successful query execution."""
        response = test_client.post(
            "/query",
            json={
                "prompt": test_prompt,
                "api_key": api_key,
                "verbose": True,
                "keep_history": True,
                "max_retries": 2,
                "timeout": 5.0
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "Hello, World!" in data["output"]
        assert isinstance(data["execution_time"], float)
        assert isinstance(data["timestamp"], str)

    @pytest.mark.api
    async def test_query_endpoint_invalid_api_key(self, test_client, test_prompt):
        """Test query with invalid API key."""
        response = test_client.post(
            "/query",
            json={
                "prompt": test_prompt,
                "api_key": "invalid_key",
                "verbose": False
            }
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.api
    async def test_query_endpoint_rate_limit(
        self, test_client, api_key, test_prompt, mock_env
    ):
        """Test query rate limiting."""
        # Make multiple requests quickly
        responses = []
        for _ in range(int(mock_env["MAX_INSTANCES"]) + 1):
            response = test_client.post(
                "/query",
                json={
                    "prompt": test_prompt,
                    "api_key": api_key
                }
            )
            responses.append(response)

        # At least one should be rate limited
        assert any(
            r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            for r in responses
        )

    @pytest.mark.api
    async def test_query_endpoint_timeout(self, test_client, api_key):
        """Test query timeout handling."""
        response = test_client.post(
            "/query",
            json={
                "prompt": "Run an infinite loop",
                "api_key": api_key,
                "timeout": 1.0
            }
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "timeout" in response.json()["detail"].lower()

    @pytest.mark.api
    async def test_query_endpoint_invalid_input(self, test_client):
        """Test query with invalid input."""
        response = test_client.post(
            "/query",
            json={
                "invalid": "data"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    async def test_query_endpoint_caching(
        self, test_client, api_key, test_prompt
    ):
        """Test response caching."""
        # First request
        response1 = test_client.post(
            "/query",
            json={
                "prompt": test_prompt,
                "api_key": api_key
            }
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second request (should be cached)
        response2 = test_client.post(
            "/query",
            json={
                "prompt": test_prompt,
                "api_key": api_key
            }
        )
        assert response2.status_code == status.HTTP_200_OK
        assert response1.json()["output"] == response2.json()["output"]

    @pytest.mark.api
    async def test_clear_cache(self, test_client):
        """Test cache clearing endpoint."""
        response = test_client.delete("/cache")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()

    @pytest.mark.api
    async def test_remove_instance(self, test_client, api_key):
        """Test instance removal endpoint."""
        # First create an instance
        test_client.post(
            "/query",
            json={
                "prompt": "test",
                "api_key": api_key
            }
        )

        # Then remove it
        response = test_client.delete(f"/instances/{api_key}")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()

        # Try to remove non-existent instance
        response = test_client.delete("/instances/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.api
    @pytest.mark.slow
    async def test_concurrent_requests(
        self, async_client, api_key, test_prompt
    ):
        """Test handling of concurrent requests."""
        import asyncio

        async def make_request():
            return await async_client.post(
                "/query",
                json={
                    "prompt": test_prompt,
                    "api_key": f"{api_key}_{id(asyncio.current_task())}",
                    "timeout": 5.0
                }
            )

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # Check all responses
        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert len(set(r.json()["output"] for r in responses)) == len(responses)

    @pytest.mark.api
    async def test_error_handling(self, test_client, api_key):
        """Test various error scenarios."""
        test_cases = [
            {
                "data": {"prompt": "", "api_key": api_key},
                "expected_status": status.HTTP_422_UNPROCESSABLE_ENTITY
            },
            {
                "data": {"prompt": "test", "api_key": "", "max_retries": -1},
                "expected_status": status.HTTP_422_UNPROCESSABLE_ENTITY
            },
            {
                "data": {"prompt": "test", "api_key": api_key, "timeout": 0},
                "expected_status": status.HTTP_422_UNPROCESSABLE_ENTITY
            }
        ]

        for case in test_cases:
            response = test_client.post("/query", json=case["data"])
            assert response.status_code == case["expected_status"]

    @pytest.mark.api
    async def test_instance_cleanup(
        self, test_client, api_key, mock_env
    ):
        """Test automatic instance cleanup."""
        # Create an instance
        response = test_client.post(
            "/query",
            json={
                "prompt": "test",
                "api_key": api_key
            }
        )
        assert response.status_code == status.HTTP_200_OK

        # Wait for cleanup
        import time
        time.sleep(int(mock_env["CACHE_TTL"]) + 1)

        # Check instance was cleaned up
        response = test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["active_instances"] == 0

    @pytest.mark.api
    async def test_response_compression(self, test_client, api_key):
        """Test response compression."""
        large_prompt = "Generate a very long response " * 100
        headers = {"Accept-Encoding": "gzip"}
        
        response = test_client.post(
            "/query",
            json={
                "prompt": large_prompt,
                "api_key": api_key
            },
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("content-encoding") == "gzip" 