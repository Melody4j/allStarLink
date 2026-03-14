"""
Application entrypoint.
"""

import argparse
import asyncio
import logging
import os
import sys

if __name__ == "__main__":
    if not os.path.exists("/app/link_scraper"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    from link_scraper.app.bootstrap import run_application
else:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from link_scraper.app.bootstrap import run_application

logger = logging.getLogger(__name__)


async def main(
    rate_limit: int | None = None,
    delay_max: float | None = None,
    delay_min: float | None = None,
    cooldown: int | None = None,
) -> None:
    await run_application(
        rate_limit=rate_limit,
        delay_max=delay_max,
        delay_min=delay_min,
        cooldown=cooldown,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neo4j topology scraper")
    parser.add_argument("rate_limit", type=int, nargs="?", default=None)
    parser.add_argument("delay_max", type=float, nargs="?", default=None)
    parser.add_argument("delay_min", type=float, nargs="?", default=None)
    parser.add_argument("cooldown", type=int, nargs="?", default=None)
    args = parser.parse_args()

    try:
        asyncio.run(
            main(
                rate_limit=args.rate_limit,
                delay_max=args.delay_max,
                delay_min=args.delay_min,
                cooldown=args.cooldown,
            )
        )
    except KeyboardInterrupt:
        logger.info("Program interrupted")
        sys.exit(0)
