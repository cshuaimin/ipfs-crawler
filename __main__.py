import asyncio
import logging
from json.decoder import JSONDecodeError
from typing import NoReturn

import magic
from aioelasticsearch import Elasticsearch

from .__init__ import ipfs, loop
from .extractors import extractors
from .ipfs import IsDirError


queue: asyncio.Queue = asyncio.Queue(maxsize=10)
es = Elasticsearch()


async def main() -> None:
    for _ in range(8):
        asyncio.ensure_future(worker())
    try:
        async for log in ipfs.log_tail():
            if log['event'] == 'handleAddProvider':
                await queue.put((log['key'], ''))
    except KeyboardInterrupt:
        logging.info('Exited')


async def worker() -> NoReturn:
    while True:
        hash, filename = await queue.get()
        logging.debug(f'Start parsing {hash} {filename}')
        try:
            doc = await parse(hash, filename)
        except asyncio.TimeoutError:
            logging.warning(f'Timed out when parsing {hash}')
        except JSONDecodeError:
            logging.warning(f'JSON decode error of {hash}')
        else:
            await add_result(doc)


async def parse(hash: str, filename: str) -> dict:
    try:
        head = await ipfs.cat(hash, length=128)
    except IsDirError:
        links = await ipfs.ls(hash)
        for link in links:
            await queue.put((link['Hash'], link['Name']))
    else:
        mime = magic.from_buffer(head, mime=True)
        doc = {
            'hash': hash,
            'filename': filename,
            'mime': mime
        }
        for type, func in extractors.items():
            if mime.startswith(type):
                doc.update(await func(hash))
                break
        return doc


async def add_result(doc: dict) -> None:
    await es.index('ipfs', '_doc', doc)


loop.run_until_complete(main())
