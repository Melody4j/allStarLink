"""
V3 module registration tests.
"""

import asyncio
import unittest

from src.link_scraper.app.context import AppContext
from src.link_scraper.app.contracts import ScheduleSpec
from src.link_scraper.app.bootstrap import load_modules
from src.link_scraper.app.scheduler import AppScheduler
from src.link_scraper.app.task_registry import TaskRegistry
from src.link_scraper.config.settings import Settings
from src.link_scraper.modules.allstarlink.module import AllStarLinkModule
from src.link_scraper.modules.allstarlink.services.node_list_snapshot_service import (
    NodeListSnapshotService,
)
from src.link_scraper.modules.other_source.tasks.source_probe.service import (
    OtherSourceProbeService,
)


class FakePriorityQueue:
    async def get_size(self):
        return 0

    async def clear(self):
        return None


class FakeBatchManager:
    async def initialize_batch_no(self, mysql_manager):
        return "202603140001"


class FakeClosable:
    async def close(self):
        return None


class FakeRedisClient(FakeClosable):
    def __init__(self) -> None:
        self.values = {}

    async def set(self, key, value):
        self.values[key] = value


class FakeMySQLManager(FakeClosable):
    def __init__(self) -> None:
        self.snapshots = []

    async def execute_statement(self, query, params=None):
        self.snapshots.append(params)


class FakeRateLimiter:
    async def can_make_request(self):
        return True


class FakeSourceClient:
    async def fetch_node_list(self):
        return {"data": [["/stats/2105", "", "", "", "", "3"], ["/stats/1001", "", "", "", "", "0"]]}

    async def close(self):
        return None


class FakeOtherSourceClient:
    async def fetch_node_list(self):
        return {"ok": True}

    async def close(self):
        return None


class FakeSourceMapper:
    def map_node_list(self, payload):
        return [
            {"node_id": 2105, "link_count": 3},
            {"node_id": 1001, "link_count": 0},
        ]


class FakeIntervalJob:
    def __init__(self) -> None:
        self.name = "fake.interval"
        self.schedule_spec = ScheduleSpec(
            mode="interval",
            interval_seconds=0.01,
            cooldown_seconds=0.01,
            max_consecutive_failures=3,
        )
        self.run_count = 0
        self.shutdown_called = False

    async def start(self) -> None:
        await self.run_once()

    async def run_once(self) -> None:
        self.run_count += 1
        if self.run_count == 1:
            raise RuntimeError("boom")

    async def shutdown(self) -> None:
        self.shutdown_called = True


class FakeContinuousJob:
    def __init__(self) -> None:
        self.name = "fake.continuous"
        self.schedule_spec = ScheduleSpec(mode="continuous")
        self.started = 0
        self.shutdown_called = False

    async def start(self) -> None:
        self.started += 1
        await asyncio.sleep(0.05)

    async def run_once(self) -> None:
        self.started += 1

    async def shutdown(self) -> None:
        self.shutdown_called = True


class FakeTimeoutJob:
    def __init__(self) -> None:
        self.name = "fake.timeout"
        self.schedule_spec = ScheduleSpec(
            mode="interval",
            interval_seconds=0.01,
            timeout_seconds=0.01,
            cooldown_seconds=0.01,
            max_consecutive_failures=1,
        )
        self.shutdown_called = False

    async def start(self) -> None:
        await self.run_once()

    async def run_once(self) -> None:
        await asyncio.sleep(0.05)

    async def shutdown(self) -> None:
        self.shutdown_called = True


class TestV3Modules(unittest.TestCase):
    def build_context(self) -> AppContext:
        # 测试默认复用 Settings.load()，这样可以覆盖真实配置装配路径。
        settings = Settings.load()
        return AppContext(
            settings=settings,
            redis_client=FakeRedisClient(),
            relational_storage_manager=FakeMySQLManager(),
            graph_storage_manager=FakeClosable(),
            priority_queue=FakePriorityQueue(),
            rate_limiter=FakeRateLimiter(),
            batch_manager=FakeBatchManager(),
        )

    def test_allstarlink_module_builds_node_topology_job(self) -> None:
        module = AllStarLinkModule()

        jobs = module.build_jobs(self.build_context())

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].name, "allstarlink.node_topology")
        self.assertEqual(jobs[1].name, "allstarlink.node_list_snapshot")
        self.assertEqual(jobs[0].schedule_spec.mode, "continuous")
        self.assertEqual(jobs[1].schedule_spec.mode, "interval")

    def test_allstarlink_module_respects_task_enabled_flags(self) -> None:
        context = self.build_context()
        context.settings.allstarlink.tasks.node_list_snapshot.enabled = False

        jobs = AllStarLinkModule().build_jobs(context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "allstarlink.node_topology")

    def test_allstarlink_module_reads_interval_from_settings(self) -> None:
        context = self.build_context()
        context.settings.allstarlink.tasks.node_list_snapshot.interval_seconds = 120

        jobs = AllStarLinkModule().build_jobs(context)

        snapshot_job = next(job for job in jobs if job.name == "allstarlink.node_list_snapshot")
        self.assertEqual(snapshot_job.schedule_spec.interval_seconds, 120)

    def test_task_registry_collects_jobs_from_module(self) -> None:
        registry = TaskRegistry()

        registry.register_module(AllStarLinkModule(), self.build_context())

        self.assertEqual(len(registry.modules), 1)
        self.assertEqual(len(registry.jobs), 2)

    def test_bootstrap_loads_other_source_module(self) -> None:
        settings = Settings.load()
        settings.source_name = "other_source"

        modules = load_modules(settings)

        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].name, "other_source")


class TestNodeListSnapshotService(unittest.IsolatedAsyncioTestCase):
    async def test_capture_snapshot_saves_summary(self) -> None:
        context = TestV3Modules().build_context()
        service = NodeListSnapshotService(context)
        service.source_components.client = FakeSourceClient()
        service.source_components.mapper = FakeSourceMapper()

        snapshot = await service.capture_snapshot()

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.node_count, 2)
        self.assertEqual(snapshot.connected_node_count, 1)
        self.assertIn("allstarlink:node_list_snapshot:last_summary", context.redis_client.values)
        self.assertEqual(len(context.relational_storage_manager.snapshots), 0)
        await service.close()


class TestOtherSourceProbeService(unittest.IsolatedAsyncioTestCase):
    async def test_probe_service_saves_last_result(self) -> None:
        context = TestV3Modules().build_context()
        context.settings.source_name = "other_source"
        service = OtherSourceProbeService(context)
        service.source_components.client = FakeOtherSourceClient()

        result = await service.run_probe()

        self.assertTrue(result.success)
        self.assertIn("other_source:probe:last_result", context.redis_client.values)
        await service.close()


class TestAppScheduler(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_isolates_interval_job_failures(self) -> None:
        interval_job = FakeIntervalJob()
        continuous_job = FakeContinuousJob()
        scheduler = AppScheduler([interval_job, continuous_job])

        scheduler_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.06)
        await scheduler.shutdown()
        await scheduler_task

        self.assertGreaterEqual(interval_job.run_count, 2)
        self.assertGreaterEqual(continuous_job.started, 1)
        self.assertTrue(interval_job.shutdown_called)
        self.assertTrue(continuous_job.shutdown_called)

        interval_state = scheduler.get_job_state("fake.interval")
        continuous_state = scheduler.get_job_state("fake.continuous")
        self.assertIsNotNone(interval_state)
        self.assertIsNotNone(interval_state.last_failure_at)
        self.assertIsNotNone(interval_state.last_success_at)
        self.assertEqual(interval_state.consecutive_failures, 0)
        self.assertIsNotNone(continuous_state.last_started_at)

    async def test_scheduler_records_timeout_failures(self) -> None:
        timeout_job = FakeTimeoutJob()
        scheduler = AppScheduler([timeout_job])

        scheduler_task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.04)
        await scheduler.shutdown()
        await scheduler_task

        state = scheduler.get_job_state("fake.timeout")
        self.assertIsNotNone(state)
        self.assertIsNotNone(state.last_failure_at)
        self.assertIn("TimeoutError", state.last_error)
        self.assertTrue(timeout_job.shutdown_called)
