import json
from typing import Dict, List, Union

import aiohttp

from .unixfs_pb2 import Data


class IsDirError(Exception):
    pass


class Ipfs:
    def __init__(self, host='127.0.0.1', port=5001):
        self.url = f'http://{host}:{port}/api/v0/'
        self.session = None

    async def request(self, path: str, arg: str = None,
                      timeout=60, **params: Union[str, int]):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        if arg:
            params['arg'] = arg
        resp = await self.session.get(
            self.url + path, params=params, timeout=timeout
        )
        if resp.status != 200:
            err = await resp.json()
            if err['Message'] == 'this dag node is a directory':
                raise IsDirError
        return resp

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

    async def log_tail(self):
        resp = await self.request('log/tail', timeout=0)
        async for line in resp.content:
            yield json.loads(line)
        resp.release()

    async def object_data(self, hash: str) -> Data:
        resp = await self.request('object/data', hash)
        data = Data()
        data.ParseFromString(await resp.read())
        resp.release()
        return data
