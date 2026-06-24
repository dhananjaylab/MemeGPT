"""
Health endpoint tests — Phase 3.

Covers:
  - GET /health returns 200 with required fields
  - GET /health/liveness returns {"alive": true}
  - check_system_resources uses run_in_executor (never blocks event loop)
  - Result is cached (second call within TTL skips executor)
  - psutil.cpu_percent is called with interval=None (not interval=1)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


class TestBasicHealth:
    @pytest.mark.asyncio
    async def test_basic_health_returns_200(self, async_client):
        resp = await async_client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_basic_health_fields(self, async_client):
        resp = await async_client.get("/health")
        body = resp.json()
        assert body["status"] == "ok"
        assert "timestamp" in body
        assert "version" in body
        assert "environment" in body

    @pytest.mark.asyncio
    async def test_liveness_returns_alive(self, async_client):
        resp = await async_client.get("/health/liveness")
        assert resp.status_code == 200
        assert resp.json()["alive"] is True


class TestSystemResourcesNonBlocking:
    """
    The Phase 2 fix moved psutil.cpu_percent(interval=1) — which sleeps
    the event loop for 1 second — into a thread executor with interval=None.
    These tests verify that fix is still in place.
    """

    @pytest.mark.asyncio
    async def test_cpu_percent_called_with_interval_none(self):
        """psutil.cpu_percent must be called with interval=None, never interval=1."""
        from routers.health import HealthChecker

        checker = HealthChecker()

        cpu_calls = []

        import psutil as _psutil

        original_cpu = _psutil.cpu_percent

        def _mock_cpu(interval=None):
            cpu_calls.append(interval)
            return 10.0

        with patch("psutil.cpu_percent", side_effect=_mock_cpu):
            result = checker._sample_system_resources()

        assert len(cpu_calls) == 1
        assert cpu_calls[0] is None, (
            "cpu_percent must be called with interval=None (non-blocking), "
            f"but was called with interval={cpu_calls[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_check_system_resources_uses_executor(self):
        """
        check_system_resources must offload to run_in_executor so blocking
        psutil calls can never stall the event loop.
        """
        from routers.health import HealthChecker

        checker = HealthChecker()
        executor_calls = []

        original_run = asyncio.get_event_loop().run_in_executor

        async def _fake_run_in_executor(executor, func, *args):
            executor_calls.append(func)
            # Call the real function synchronously so we get a real result
            return func(*args)

        loop = asyncio.get_event_loop()
        with patch.object(loop, "run_in_executor", side_effect=_fake_run_in_executor):
            result = await checker.check_system_resources()

        assert len(executor_calls) >= 1, (
            "check_system_resources must call run_in_executor at least once"
        )
        assert "cpu" in result
        assert "memory" in result

    @pytest.mark.asyncio
    async def test_result_is_cached_within_ttl(self):
        """
        Two rapid calls to check_system_resources must return the same
        object (cache hit) — the second must not re-invoke run_in_executor.
        """
        from routers.health import HealthChecker

        checker = HealthChecker()
        checker._system_cache_ttl = 5.0  # 5-second TTL

        call_count = 0

        async def _fake_executor(executor, func, *args):
            nonlocal call_count
            call_count += 1
            return func(*args)

        loop = asyncio.get_event_loop()
        with patch.object(loop, "run_in_executor", side_effect=_fake_executor):
            r1 = await checker.check_system_resources()
            r2 = await checker.check_system_resources()

        # First call hits executor, second is served from cache
        assert call_count == 1, (
            f"Expected 1 executor call (second should be cached), got {call_count}"
        )
        assert r1 is r2  # same object reference from cache

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """After TTL expires, the next call must re-sample."""
        import time
        from routers.health import HealthChecker

        checker = HealthChecker()
        checker._system_cache_ttl = 0.01  # 10ms TTL

        call_count = 0

        async def _fake_executor(executor, func, *args):
            nonlocal call_count
            call_count += 1
            return func(*args)

        loop = asyncio.get_event_loop()
        with patch.object(loop, "run_in_executor", side_effect=_fake_executor):
            await checker.check_system_resources()
            await asyncio.sleep(0.05)  # wait for TTL to expire
            await checker.check_system_resources()

        assert call_count == 2


class TestSystemResourcesThresholds:
    """Verify the status thresholds in _sample_system_resources."""

    def _sample_with(self, cpu=10.0, mem_pct=50.0, disk_pct=50.0):
        from routers.health import HealthChecker
        import psutil

        mem = MagicMock()
        mem.percent = mem_pct
        mem.available = 4 * 1024 ** 3
        mem.total = 8 * 1024 ** 3

        disk = MagicMock()
        disk.percent = disk_pct
        disk.free = 50 * 1024 ** 3
        disk.total = 100 * 1024 ** 3

        with (
            patch("psutil.cpu_percent", return_value=cpu),
            patch("psutil.virtual_memory", return_value=mem),
            patch("psutil.disk_usage", return_value=disk),
            patch("psutil.cpu_count", return_value=4),
        ):
            return HealthChecker._sample_system_resources()

    def test_healthy_below_thresholds(self):
        result = self._sample_with(cpu=50.0, mem_pct=70.0, disk_pct=60.0)
        assert result["status"] == "healthy"

    def test_degraded_on_high_cpu(self):
        result = self._sample_with(cpu=85.0)
        assert result["status"] == "degraded"
        assert any("CPU" in w for w in result.get("warnings", []))

    def test_degraded_on_high_memory(self):
        result = self._sample_with(mem_pct=87.0)
        assert result["status"] == "degraded"

    def test_critical_on_extreme_cpu(self):
        result = self._sample_with(cpu=97.0)
        assert result["status"] == "critical"

    def test_result_has_required_keys(self):
        result = self._sample_with()
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "percent" in result["cpu"]
        assert "percent" in result["memory"]
        assert "percent" in result["disk"]
