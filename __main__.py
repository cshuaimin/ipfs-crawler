import asyncio

from .crawler import Crawler


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
