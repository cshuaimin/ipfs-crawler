import asyncio
import logging
import pickle
from typing import NoReturn, Set, Union

import magic
from aioelasticsearch import Elasticsearch

from .__init__ import ipfs, loop
from .extractors import extractors
from .ipfs import IsDirError, IpfsError


queue: asyncio.Queue = asyncio.Queue(maxsize=10)
es = Elasticsearch()
parsed: Set[str] = set()


async def main() -> None:
    try:
        global parsed
        with open('parsed.pickle', 'rb') as f:
            parsed = pickle.load(f)
    except FileNotFoundError:
        pass

    # start consumers
    for _ in range(8):
        asyncio.ensure_future(worker())
    # start producing..
    async for log in ipfs.log_tail():
        if log['event'] == 'handleAddProvider':
            await queue.put((log['key'], ''))


async def worker() -> NoReturn:
    while True:
        hash, filename = await queue.get()
        if hash in parsed:
            logging.info(f'Ignored {hash}')
            continue
        parsed.add(hash)
        try:
            doc = await parse(hash, filename)
            if doc is not None:
                await add_result(doc)
        except asyncio.TimeoutError:
            logging.warning(f'{hash} timed out')
        except IpfsError as exc:
            logging.warning(f'{hash}: {exc}')


async def parse(hash: str, filename: str) -> Union[dict, None]:
    logging.info(f'Parsing {hash} {filename}')
    try:
        head = await ipfs.cat(hash, length=128)
    # This hash is a directory, add files in it to the queue. There is
    # currently no good way to determine if it's a file or a directory.
    except IsDirError:
        links = await ipfs.ls(hash)
        for link in links:
            await queue.put((link['Hash'], link['Name']))
        return None

    mime = magic.from_buffer(head, mime=True)
    # Basic info, more in-depth info will be parsed in the extractor function.
    doc = {
        'hash': hash,
        'filename': filename,
        'mime': mime
    }
    try:
        extract = extractors[mime.split('/')[0]]
    except KeyError:
        # If there is no extractor, don't save it.
        return None
    else:
        doc.update(await extract(hash))
        return doc


async def add_result(doc: dict) -> None:
    hash = doc['hash']
    index, _ = doc['mime'].split('/')
    await es.index(index, '_doc', body=doc, id=hash)
    logging.info(f"Indexed {hash} {doc['mime']}")


try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
finally:
    with open('parsed.pickle', 'wb') as f:
        pickle.dump(parsed, f)
    logging.info('Exited')
