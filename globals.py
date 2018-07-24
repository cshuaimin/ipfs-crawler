import asyncio
import logging

from aioelasticsearch import Elasticsearch

from .ipfs import Ipfs

logging.basicConfig(level=logging.INFO, format='%(message)s')
ipfs = Ipfs()
loop = asyncio.get_event_loop()
es = Elasticsearch()
