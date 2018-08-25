import json
import logging
import re
from json import JSONDecoder
from typing import AsyncIterator, Dict, List, Union

import aiohttp

log = logging.getLogger(__name__)
NOT_WHITESPACE = re.compile(r'[^\s]')


class IsDirError(Exception):
    pass


class IpfsError(Exception):
    pass


def decode_stacked(document, pos=0, decoder=JSONDecoder()):
    while True:
        match = NOT_WHITESPACE.search(document, pos)
        if not match:
            return
        pos = match.start()
        obj, pos = decoder.raw_decode(document, pos)
        yield obj


class Ipfs:
    def __init__(self, host='127.0.0.1', port=5001) -> None:
        self.url = f'http://{host}:{port}/api/v0/'
        self.session: aiohttp.ClientSession = None

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def request(self, path: str, arg: str = None,
                      timeout=60, **params: Union[str, int]):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        if arg:
            params['arg'] = arg
        resp = await self.session.get(
            self.url + path, params=params, timeout=timeout
        )
        if resp.status == 200:
            return resp

        err = await resp.json()
        if err['Message'] == 'this dag node is a directory':
            raise IsDirError
        else:
            raise IpfsError(err['Message'])

    # https://ipfs.io/docs/api/ and search 'v0/ls'
    async def ls(self, hash: str) -> List[Dict[str, Union[int, str]]]:
        resp = await self.request('ls', hash)
        result = json.loads(await resp.text())
        resp.release()
        return result['Objects'][0]['Links']

    async def cat(self, hash: str, offset: int = 0, length: int = -1) -> bytes:
        kw = {}
        if offset != 0:
            kw['offset'] = offset
        if length != -1:
            kw['length'] = length
        resp = await self.request('cat', hash, **kw)
        data = await resp.read()
        resp.release()
        return data

    async def log_tail(self) -> AsyncIterator[dict]:
        while True:
            resp = await self.request('log/tail', timeout=0)
            async for data in resp.content.iter_any():
                for obj in decode_stacked(data.decode()):
                    yield obj
            resp.release()
            log.warning('Log tail finished! Restarted')
