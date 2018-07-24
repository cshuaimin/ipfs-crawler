import asyncio
import logging
import pickle
from asyncio import Future
from typing import List, NoReturn, Set, Union

import magic

from .apiserver import start_server, stop_server
from .extractors import extractors
from .globals import es, ipfs, loop
from .ipfs import IpfsError, IsDirError

queue: asyncio.Queue = asyncio.Queue(maxsize=10)
parsed: Set[str] = set()
workers: List[Future] = []


async def main() -> None:
    # start the REST API server
    await start_server()

    try:
        global parsed
        with open('parsed.pickle', 'rb') as f:
            parsed = pickle.load(f)
    except FileNotFoundError:
        pass

    # start consumers
    for _ in range(8):
        workers.append(asyncio.ensure_future(worker()))
    logging.info('Started')
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


async def cleanup() -> None:
    logging.info('Stopping the workers...')
    for f in workers:
        f.cancel()
    await asyncio.wait(workers)
    await stop_server()
    await es.close()
    await ipfs.close()


try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
finally:
    loop.run_until_complete(cleanup())
    with open('parsed.pickle', 'wb') as f:
        pickle.dump(parsed, f)
    loop.close()
