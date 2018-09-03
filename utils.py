import asyncio
from sys import stderr
from typing import Callable

from termcolor import colored

levels = {
    'debug': colored('[~]', 'white', attrs=['bold']),
    'info': colored('[+]', 'green', attrs=['bold']),
    'warning': colored('[!]', 'yellow', attrs=['bold']),
    'error': colored('[-]', 'red', attrs=['bold'])
}


def log(level: str, msg: str) -> None:
    print(f'{levels[level]} {msg}', file=stderr, flush=True)


async def retry(func: Callable, name: str, *errors: Exception):
    for _ in range(10):
        try:
            return await func()
        except Exception as exc:
            if any(isinstance(exc, err) for err in errors):
                log('warning', f'Waiting for {name}')
                await asyncio.sleep(4)
            else:
                raise
    else:
        raise SystemExit(f'Why is the {name} not yet started?')
