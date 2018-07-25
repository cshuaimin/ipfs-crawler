import asyncio
import logging
import pickle
from asyncio import Future
from typing import List, NoReturn, Set, Union

import magic

from .apiserver import start_server, stop_server
from .extractors import extractors
from .globals import es, ipfs
from .ipfs import IsDirError


class Crawler:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.workers: List[Future] = []
        try:
            with open('parsed.pickle', 'rb') as f:
                self.parsed: Set[str] = pickle.load(f)
        except FileNotFoundError:
            pass

    async def run(self) -> None:
        # start the REST API server
        await start_server()
        # start consumers
        for _ in range(8):
            self.workers.append(asyncio.ensure_future(self.worker()))
        # start producer
        self.producer: Future = asyncio.ensure_future(self.read_logs())
        logging.info('Started')
        await self.producer

    async def stop(self) -> None:
        # cancel producer and consumer
        self.producer.cancel()
        for w in self.workers:
            w.cancel()
        # ensure exited
        await asyncio.gather(
            self.producer, *self.workers, return_exceptions=True
        )

        # cleanup
        await asyncio.gather(ipfs.close(), stop_server())
        # Close ES after API server, because server needs it.
        await es.close()

        with open('parsed.pickle', 'wb') as f:
            pickle.dump(self.parsed, f)
        logging.info('Exited')

    async def read_logs(self) -> NoReturn:
        async for log in ipfs.log_tail():
            if log['event'] == 'handleAddProvider':
                await self.queue.put((log['key'], ''))

    async def worker(self) -> NoReturn:
        while True:
            hash, filename = await self.queue.get()
            if hash in self.parsed:
                logging.info(f'Ignored {hash}')
                continue
            self.parsed.add(hash)
            try:
                doc = await self.parse(hash, filename)
                if doc is not None:
                    await self.add_result(doc)
            except asyncio.TimeoutError:
                logging.warning(f'{hash} timed out')
            except Exception as exc:
                logging.warning(f'{hash}: {exc!r}')

    async def parse(self, hash: str, filename: str) -> Union[dict, None]:
        logging.info(f'Parsing {hash} {filename}')
        try:
            head = await ipfs.cat(hash, length=128)
        # This hash is a directory, add files in it to the queue. There is
        # currently no good way to determine if it's a file or a directory.
        except IsDirError:
            links = await ipfs.ls(hash)
            for link in links:
                await self.queue.put((link['Hash'], link['Name']))
            return None

        mime = magic.from_buffer(head, mime=True)
        # Basic information, more in-depth information will be parsed
        # in the extractor function.
        doc = {
            'hash': hash,
            'filename': filename,
            'mime': mime
        }
        try:
            extract = extractors[mime]
        except KeyError:
            if mime.startswith(('video', 'image')):
                return doc
            else:
                return None
        else:
            doc.update(await extract(hash))
            return doc

    async def add_result(self, doc: dict) -> None:
        hash = doc['hash']
        index = doc['mime'].replace('/', '-')
        await es.index(index, '_doc', body=doc, id=hash)
        logging.info(f"Indexed {hash} {doc['mime']}")
