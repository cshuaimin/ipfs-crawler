from typing import Callable, Dict

import tika.parser

from .__init__ import ipfs, loop

extractors: Dict[str, Callable] = {}


def extractor(mime):
    def decorator(func: Callable):
        extractors[mime] = func
        return func
    return decorator


@extractor('text')
async def text_info(hash: str) -> dict:
    text = await ipfs.cat(hash)
    res = await loop.run_in_executor(None, tika.parser.from_buffer, text)
    metadata = res['metadata']
    if not metadata['Content-Type'].startswith('text'):
        return {}
    info = {'content': res['content']}
    if 'title' in metadata:
        info['title'] = metadata['title']
    if 'description' in metadata:
        info['description'] = metadata['description']
    return info
