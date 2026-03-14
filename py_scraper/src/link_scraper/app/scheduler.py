"""
统一调度器。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List

from .contracts import ScheduledJob

logger = logging.getLogger(__name__)


@dataclass
class JobRuntimeState:
    """记录单个任务的运行状态，供调试、监控和后续可观测性扩展使用。"""

    name: str
    is_running: bool = False
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    next_run_at: datetime | None = None
    consecutive_failures: int = 0
    last_error: str | None = None


class AppScheduler:
    def __init__(self, jobs: Iterable[ScheduledJob]) -> None:
        self.jobs: List[ScheduledJob] = list(jobs)
        self._tasks: List[asyncio.Task] = []
        self.job_states = {
            job.name: JobRuntimeState(name=job.name)
            for job in self.jobs
        }

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._run_job(job), name=job.name)
            for job in self.jobs
        ]
        if not self._tasks:
            return
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        for job in self.jobs:
            await job.shutdown()

    def get_job_state(self, job_name: str) -> JobRuntimeState | None:
        """返回指定任务的最新运行状态。"""
        return self.job_states.get(job_name)

    async def _run_job(self, job: ScheduledJob) -> None:
        mode = job.schedule_spec.mode

        # manual 类型的任务允许被注册，但默认不参与统一调度，
        # 为后续手工补数、调试执行预留入口。
        if mode == "manual":
            logger.info("Skipping manual job registration for %s", job.name)
            return

        if mode == "interval":
            await self._run_interval_job(job)
            return

        await self._run_continuous_job(job)

    async def _run_continuous_job(self, job: ScheduledJob) -> None:
        while True:
            try:
                await self._execute_with_state(job, job.start)
                # continuous 任务理论上应当常驻运行。
                # 如果异常退出，scheduler 负责自动拉起，避免整个应用停摆。
                logger.warning("Continuous job %s exited unexpectedly, restarting", job.name)
                self._set_next_run(job.name, 1)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                cooldown_seconds = self._get_cooldown_seconds(job)
                logger.exception("Continuous job %s failed; cooling down for %s seconds", job.name, cooldown_seconds)
                self._set_next_run(job.name, cooldown_seconds)
                await asyncio.sleep(cooldown_seconds)

    async def _run_interval_job(self, job: ScheduledJob) -> None:
        interval_seconds = job.schedule_spec.interval_seconds or 60
        while True:
            try:
                # interval 任务每轮只执行一次 run_once。
                # 单轮失败只记录日志并继续下一轮，不影响其他任务。
                await self._execute_with_state(job, job.run_once)
            except asyncio.CancelledError:
                raise
            except Exception:
                cooldown_seconds = self._get_cooldown_seconds(job)
                logger.exception("Interval job %s failed; cooling down for %s seconds", job.name, cooldown_seconds)
                self._set_next_run(job.name, cooldown_seconds)
                await asyncio.sleep(cooldown_seconds)
                continue

            self._set_next_run(job.name, interval_seconds)
            await asyncio.sleep(interval_seconds)

    async def _execute_with_state(self, job: ScheduledJob, runner) -> None:
        state = self.job_states[job.name]
        state.is_running = True
        state.last_started_at = datetime.now()
        state.last_error = None

        try:
            timeout_seconds = job.schedule_spec.timeout_seconds
            if timeout_seconds:
                await asyncio.wait_for(runner(), timeout=timeout_seconds)
            else:
                await runner()
        except asyncio.CancelledError:
            state.last_finished_at = datetime.now()
            state.is_running = False
            raise
        except Exception as exc:
            state.last_finished_at = datetime.now()
            state.last_failure_at = state.last_finished_at
            state.consecutive_failures += 1
            state.last_error = f"{exc.__class__.__name__}: {exc}" if str(exc) else exc.__class__.__name__
            state.is_running = False
            raise
        else:
            state.last_finished_at = datetime.now()
            state.last_success_at = state.last_finished_at
            state.consecutive_failures = 0
            state.is_running = False

    def _get_cooldown_seconds(self, job: ScheduledJob) -> float:
        state = self.job_states[job.name]
        threshold = max(1, job.schedule_spec.max_consecutive_failures)
        if state.consecutive_failures >= threshold:
            # 连续失败达到阈值后，使用更长冷却时间，避免持续快速重试。
            return max(job.schedule_spec.cooldown_seconds, 30.0)
        return job.schedule_spec.cooldown_seconds

    def _set_next_run(self, job_name: str, delay_seconds: float) -> None:
        self.job_states[job_name].next_run_at = datetime.now() + timedelta(seconds=delay_seconds)
