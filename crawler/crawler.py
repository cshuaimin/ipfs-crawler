import asyncio
from asyncio import Future
from dataclasses import dataclass, field
from functools import partial
from socket import gaierror
from typing import List, NoReturn, Union

import asyncpg
import magic
from bs4 import BeautifulSoup
from pybloom_live import ScalableBloomFilter

from ipfs import Ipfs, IpfsError, IsDirError
from utils import retry, log



@dataclass
class HtmlInfo:
    title: str
    # text is too long
    text: str = field(repr=False)
    hash: str = ''
    filename: str = ''


class Crawler:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.workers: List[Future] = []
        self.ipfs = Ipfs()

    async def run(self) -> None:
        try:
            with open('/data/bloom-filter', 'rb') as f:
                log('debug', 'Using saved bloom-filter')
                self.filter = ScalableBloomFilter.fromfile(f)
        except FileNotFoundError:
            log('debug', 'Creating new bloom-filter')
            self.filter = ScalableBloomFilter(initial_capacity=100000)

        self.conn_pool = await retry(
            partial(
                asyncpg.create_pool,
                host='db',
                user='postgres',
                database='ipfs_crawler'
            ),
            'database',
            gaierror, ConnectionRefusedError, asyncpg.CannotConnectNowError
        )

        # start consumers
        for _ in range(8):
            self.workers.append(asyncio.ensure_future(self.worker()))
        # start producer
        self.producer: Future = asyncio.ensure_future(self.read_logs())
        log('info', 'Started crawling')

        # If an exception is thrown in the background task,
        # our crawler should not ignore it and continue to run, but throws it.
        await asyncio.gather(self.producer, *self.workers)

    async def stop(self) -> None:
        # cancel producer and consumer
        self.producer.cancel()
        for w in self.workers:
            w.cancel()
        # ensure exited
        res = await asyncio.gather(
            self.producer, *self.workers, return_exceptions=True
        )
        for exc in res:
            if not isinstance(exc, asyncio.CancelledError):
                log('error', repr(exc))

        log('debug', 'Saving bloom-filter')
        with open('/data/bloom-filter', 'wb') as f:
            self.filter.tofile(f)

        await asyncio.gather(self.ipfs.close(), self.conn_pool.close())
        log('info', 'Exited')

    async def read_logs(self) -> NoReturn:
        while True:
            async with self.ipfs.log_tail() as log_iter:
                async for event in log_iter:
                    if event.get('Operation') == 'handleAddProvider':
                        await self.queue.put((event['Tags']['key'], ''))
            log('warning', 'Log tail restarted')

    async def worker(self) -> NoReturn:
        while True:
            hash, filename = await self.queue.get()
            if hash in self.filter:
                continue
            self.filter.add(hash)
            try:
                info = await self.parse(hash, filename)
                if info is not None:
                    await self.add_result(info)
            except asyncio.CancelledError:
                # self.parse() will probably raise CancelledError
                # when self.stop() called. Won't log this.
                raise
            except asyncio.TimeoutError:
                log('warning', f'Timed out: {hash}')
            except IpfsError as exc:
                log('error', repr(exc))
            except Exception as exc:
                log('error', f'Failed to parse {hash}, worker exited: {exc!r}')
                raise

    async def parse(self, hash: str, filename: str) -> Union[HtmlInfo, None]:
        try:
            head = await self.ipfs.cat(hash, length=128)
        # This hash is a directory, add files in it to the queue. There is
        # currently no good way to determine if it's a file or a directory.
        except IsDirError:
            links = await self.ipfs.ls(hash)
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
        if mime != 'text/html':
            return None
        info = await self.parse_html(hash)
        info.hash = hash
        info.filename = filename
        return info

    async def parse_html(self, hash: str) -> HtmlInfo:
        html = (await self.ipfs.cat(hash)).decode()
        soup = BeautifulSoup(html, 'html.parser')
        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.extract()    # rip it out

        # get text
        text = soup.get_text()

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (
            phrase.strip() for line in lines for phrase in line.split('  ')
        )
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return HtmlInfo(
            title=soup.title.string if soup.title else '',
            text=text
        )

    async def add_result(self, info: HtmlInfo) -> None:
        await self.conn_pool.execute(
            'INSERT INTO html(hash, filename, title, text) '
            'values ($1, $2, $3, $4)',
            # dataclass is not iterable
            info.hash, info.filename, info.title, info.text
        )


if __name__ == '__main__':
    import sys
    print('''
██╗██████╗ ███████╗███████╗     ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗ 
██║██╔══██╗██╔════╝██╔════╝    ██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
██║██████╔╝█████╗  ███████╗    ██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
██║██╔═══╝ ██╔══╝  ╚════██║    ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
██║██║     ██║     ███████║    ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
╚═╝╚═╝     ╚═╝     ╚══════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
    ''', file=sys.stderr, flush=True)
    loop = asyncio.get_event_loop()
    crawler = Crawler()
    try:
        loop.run_until_complete(crawler.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(crawler.stop())
        loop.close()
