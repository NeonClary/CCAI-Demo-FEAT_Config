"""Standalone scheduler entrypoint for the Docker scheduler service."""
import asyncio
from app.core.scheduler import init_scheduler


async def main():
    init_scheduler()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
