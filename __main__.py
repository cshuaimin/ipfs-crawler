import asyncio
import logging
import pickle
from json.decoder import JSONDecodeError
from typing import NoReturn, Set

import magic
from aioelasticsearch import Elasticsearch
from aiohttp import ClientError

from .__init__ import ipfs, loop
from .extractors import extractors
from .ipfs import IsDirError


queue: asyncio.Queue = asyncio.Queue(maxsize=10)
es = Elasticsearch()
parsed: Set[str] = set()


async def main() -> None:
    try:
        with open('parsed.pickle', 'rb') as f:
            parsed = pickle.load(f)
    except FileNotFoundError:
        pass
    for _ in range(8):
        asyncio.ensure_future(worker())
    async for log in ipfs.log_tail():
        if log['event'] == 'handleAddProvider':
            await queue.put((log['key'], ''))


async def worker() -> NoReturn:
    while True:
        hash, filename = await queue.get()
        if hash in parsed:
            logging.info(f'{hash} has been parsed, ignored')
            continue
        parsed.add(hash)
        logging.info(f'Parsing {hash} {filename}')
        try:
            try:
                head = await ipfs.cat(hash, length=128)
            except IsDirError:
                links = await ipfs.ls(hash)
                for link in links:
                    await queue.put((link['Hash'], link['Name']))
                continue
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
                if mime.startswith('text'):
                    await add_result(doc)
        except asyncio.TimeoutError:
            logging.warning(f'Timed out when parsing {hash}')
        except JSONDecodeError:
            logging.warning(f'JSON decode error of {hash}')
        except ClientError as exc:
            logging.warning(f'{hash}: {exc!r}')


async def add_result(doc: dict) -> None:
    hash = doc['hash']
    await es.index('ipfs', '_doc', body=doc, id=hash)
    logging.info(f"Indexed {hash} {doc['mime']}")


try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    with open('parsed.pickle', 'wb') as f:
        pickle.dump(parsed, f)
    logging.info('Exited')
