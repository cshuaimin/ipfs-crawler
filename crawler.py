import asyncio
import logging
import pickle
from asyncio import Future
from typing import List, NoReturn, Set, Union

import magic

from .apiserver import start_server, stop_server
from .extractors import extractors
from .globals import es, ipfs
from .ipfs import IsDirError, IpfsError

log = logging.getLogger(__name__)


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
        log.info('Started crawling...')
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
        log.info('Exited')

    async def read_logs(self) -> NoReturn:
        async for log in ipfs.log_tail():
            if log['event'] == 'handleAddProvider':
                await self.queue.put((log['key'], ''))

    async def worker(self) -> NoReturn:
        while True:
            hash, filename = await self.queue.get()
            if hash in self.parsed:
                log.debug(f'Ignored {hash}')
                continue
            self.parsed.add(hash)
            try:
                doc = await self.parse(hash, filename)
            except asyncio.CancelledError:
                # self.parse() will probably raise CancelledError
                # when self.stop() called. Won't log this.
                raise
            except asyncio.TimeoutError:
                log.warning(f'{hash} timed out')
            except IpfsError as exc:
                log.error(exc)
            except Exception as exc:
                log.error(f'Failed to parse {hash}, worker exited: {exc!r}')
                raise
            else:
                if doc is not None:
                    await self.add_result(doc)

    async def parse(self, hash: str, filename: str) -> Union[dict, None]:
        log.debug(f'Parsing {hash} {filename}')
        try:
            head = await ipfs.cat(hash, length=128)
        # This hash is a directory, add files in it to the queue. There is
        # currently no good way to determine if it's a file or a directory.
        except IsDirError:
            links = await ipfs.ls(hash)
            for link in links:
                # Using `await self.queue.put()` will block the worker, if all
                # workers are blocked, the crawler will fall into a deadlock.
                # Note: the queue won't increase infinitely because:
                #   1. if the queue's size >= max size, the producer will stop
                #      production
                #   2. the files in the directory are not unlimited, they will
                #      be used up sooner or later.
                self.queue._queue.append((link['Hash'], link['Name']))
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
        log.info(
            f"Indexed {hash} mime={doc['mime']} {doc['filename']}"
        )
