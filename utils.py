import asyncio
import logging

from typing import Callable


log = logging.getLogger(__name__)


async def retry(func: Callable, name: str, *errors: Exception):
    for _ in range(10):
        try:
            return await func()
        except Exception as exc:
            if any(isinstance(exc, err) for err in errors):
                log.warning(f'Waiting for {name}..')
                await asyncio.sleep(4)
            else:
                raise
    else:
        raise SystemExit(f'Why is the {name} not yet started?')
