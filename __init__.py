import asyncio
import logging

from .ipfs import Ipfs


logging.basicConfig(level=logging.DEBUG)
ipfs = Ipfs()
loop = asyncio.get_event_loop()
