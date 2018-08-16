import asyncio
import logging
from asyncio import Future
from dataclasses import dataclass
from typing import List, NoReturn, Union

import asyncpg
import magic
from bs4 import BeautifulSoup

from ipfs import Ipfs, IpfsError, IsDirError

log = logging.getLogger(__name__)


@dataclass
class HtmlInfo:
    title: str
    text: str
    hash: str = ''
    filename: str = ''


class Crawler:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.workers: List[Future] = []
        self.ipfs = Ipfs()

    async def run(self) -> None:
        self.conn_pool = await asyncpg.create_pool(
            user='postgres',
            database='ipfs_crawler'
        )
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
            # FIXME: Don't ignore exceptions
            self.producer, *self.workers, return_exceptions=True
        )
        await asyncio.gather(self.ipfs.close(), self.conn_pool.close())
        log.info('Exited')

    async def read_logs(self) -> NoReturn:
        while True:
            await asyncio.sleep(10000)
        # async for log in self.ipfs.log_tail():
            # if log['event'] == 'handleAddProvider':
            #     await self.queue.put((log['key'], ''))

    async def worker(self) -> NoReturn:
        while True:
            hash, filename = await self.queue.get()
            if await self.parsed(hash):
                log.debug(f'Ignored {hash}')
                continue
            await self.add_parsed(hash)
            try:
                info = await self.parse(hash, filename)
                if info is not None:
                    await self.add_result(info)
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

    async def parse(self, hash: str, filename: str) -> Union[HtmlInfo, None]:
        log.debug(f'Parsing {hash} {filename}')
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

        return HtmlInfo(title=soup.title.string, text=text)

    async def add_result(self, info: HtmlInfo) -> None:
        self.conn_pool.execute(
            'INSERT INTO html(hash, filename, title, text) '
            'values ($1, $2, $3, $4, $5)',
            *info
        )

    async def parsed(self, hash: str) -> bool:
        return bool(await self.conn_pool.fetchval(
            'SELECT count(1) from parsed where hash = $1', hash
        ))

    async def add_parsed(self, hash: str) -> None:
        await self.conn_pool.execute(
            'INSERT INTO parsed(hash) VALUES ($1)', hash
        )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    crawler = Crawler()
    try:
        loop.run_until_complete(crawler.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(crawler.stop())
        loop.close()
