import asyncio
import json
from contextlib import asynccontextmanager
from json import JSONDecodeError, JSONDecoder
from typing import Dict, List, Union

import aiohttp


class IsDirError(Exception):
    pass


class IpfsError(Exception):
    pass


class StackedJson:
    """Parse stacked json objects sent in an infinite stream, i.e.:
        {"k1":"v1"}
        [1,2]
        {"k2":"v2"}
        [3,4]
    """
    def __init__(self) -> None:
        self.raw_decode = JSONDecoder().raw_decode
        self.queue = asyncio.Queue(maxsize=16)

    async def add(self, part: str) -> None:
        await self.queue.put(part)

    async def __aiter__(self):
        buffer = await self.queue.get()
        if buffer is None:
            return
        pos = 0
        while True:
            try:
                # `raw_decode` doesn't accept strings that have
                # prefixing whitespace. So we need to search to find
                # the first none-whitespace part of out document.
                while len(buffer) > pos and buffer[pos].isspace():
                    pos += 1
                obj, pos = self.raw_decode(buffer, pos)
            except JSONDecodeError:
                part = await self.queue.get()
                if part is None:
                    return
                buffer = buffer[pos:] + part
                pos = 0
            else:
                yield obj


class Ipfs:
    def __init__(self, host='127.0.0.1', port=5001) -> None:
        self.url = f'http://{host}:{port}/api/v0/'
        self.session: aiohttp.ClientSession = None

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()

    @asynccontextmanager
    async def request(self, path: str, arg: str = None,
                      timeout=60, **params: Union[str, int]):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        if arg:
            params['arg'] = arg
        async with self.session.get(
            self.url + path, params=params, timeout=timeout
        ) as resp:
            if resp.status == 200:
                yield resp
            else:
                err = await resp.json()
                if err['Message'] == 'this dag node is a directory':
                    raise IsDirError
                else:
                    raise IpfsError(err['Message'])

    # https://ipfs.io/docs/api/ and search 'v0/ls'
    async def ls(self, hash: str) -> List[Dict[str, Union[int, str]]]:
        async with self.request('ls', hash) as resp:
            result = json.loads(await resp.text())
            return result['Objects'][0]['Links']

    async def cat(self, hash: str, offset: int = 0, length: int = -1) -> bytes:
        kw = {}
        if offset != 0:
            kw['offset'] = offset
        if length != -1:
            kw['length'] = length
        async with self.request('cat', hash, **kw) as resp:
            return await resp.read()

    @asynccontextmanager
    async def log_tail(self):
        async with self.request('log/tail', timeout=0) as resp:

            async def add():
                async for data in resp.content.iter_any():
                    await sj.add(data.decode())

            sj = StackedJson()
            fut = asyncio.ensure_future(add())

            try:
                yield sj
            finally:
                fut.cancel()
                await fut
