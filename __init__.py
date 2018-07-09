import asyncio
import logging

from .ipfs import Ipfs


logging.basicConfig(level=logging.INFO, format='%(message)s')
ipfs = Ipfs()
loop = asyncio.get_event_loop()
