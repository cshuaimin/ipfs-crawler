import asyncio
from typing import Callable, Dict
from bs4 import BeautifulSoup

from .globals import ipfs

extractors: Dict[str, Callable] = {}
loop = asyncio.get_event_loop()


def extractor(mime):
    def decorator(func: Callable):
        extractors[mime] = func
        return func
    return decorator


def get_text(html: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text


@extractor('text/html')
async def clean_html(hash: str) -> dict:
    html = (await ipfs.cat(hash)).decode()
    return {
        'text': get_text(html)
    }
