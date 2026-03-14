"""
Application bootstrap for the V3 modular runtime.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import List

from ..config.settings import Settings
from ..modules.allstarlink.module import AllStarLinkModule
from ..modules.other_source.module import OtherSourceModule
from .container import AppContainer
from .contracts import SourceModule
from .scheduler import AppScheduler
from .task_registry import TaskRegistry

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    logging.getLogger("link_scraper").setLevel(log_level)


def load_modules(settings: Settings) -> List[SourceModule]:
    """按配置加载启用的 source module。

    V3 的关键边界是：
    1. 入口层只决定启用哪个 source module
    2. module 自己负责返回其下的 jobs
    3. scheduler 不关心具体 source 的内部细节
    """
    if settings.source_name == "allstarlink" and settings.allstarlink.enabled:
        return [AllStarLinkModule()]

    # 第二数据源当前先接入最小 module 骨架，
    # 用于验证 source 横向扩展不需要修改 main.py 或 scheduler 核心逻辑。
    if settings.source_name == "other_source":
        return [OtherSourceModule()]

    raise ValueError(f"Unsupported source module: {settings.source_name}")


def apply_runtime_overrides(
    settings: Settings,
    rate_limit: int | None = None,
    delay_max: float | None = None,
    delay_min: float | None = None,
    cooldown: int | None = None,
) -> Settings:
    if rate_limit is not None:
        settings.network.rate_limit = rate_limit
    if delay_max is not None:
        settings.network.request_delay_max = delay_max
    if delay_min is not None:
        settings.network.request_delay_min = delay_min
    if cooldown is not None:
        settings.network.cooldown_429 = cooldown
    return settings


async def run_application(
    rate_limit: int | None = None,
    delay_max: float | None = None,
    delay_min: float | None = None,
    cooldown: int | None = None,
) -> None:
    configure_logging()
    settings = apply_runtime_overrides(
        Settings.load(),
        rate_limit=rate_limit,
        delay_max=delay_max,
        delay_min=delay_min,
        cooldown=cooldown,
    )

    container = AppContainer(settings)
    context = await container.build_context()
    registry = TaskRegistry()

    for module in load_modules(settings):
        registry.register_module(module, context)

    scheduler = AppScheduler(registry.jobs)
    stop_event = asyncio.Event()

    def handle_signal(signum, frame) -> None:
        logger.info("Received signal %s, shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    scheduler_task = asyncio.create_task(scheduler.start(), name="app-scheduler")
    stop_task = asyncio.create_task(stop_event.wait(), name="app-stop-wait")

    try:
        done, pending = await asyncio.wait(
            {scheduler_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        for task in done:
            if task is scheduler_task:
                await task
    finally:
        await scheduler.shutdown()
        await container.close_context(context)
