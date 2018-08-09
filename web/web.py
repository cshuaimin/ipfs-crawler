import logging
import asyncpg

from aiohttp import web

routes = web.RouteTableDef()
runner: web.AppRunner = None
log = logging.getLogger(__name__)


@routes.get('/search/{query}')
async def search(request: web.Request) -> web.Response:
    result = await request.app['pg'].fetchrow(
        "select * from tab where col @@ to_tsquery('english','help')"
    )
    print(repr(result))
    return web.json_response(
        result,
        headers={'Access-Control-Allow-Origin': '*'}
    )


async def pg_conn(app: web.Application) -> None:
    app['pg'] = await asyncpg.connect(database='test')
    yield
    await app['pg'].close()

async def start_server() -> None:
    global runner
    app = web.Application()
    app.cleanup_ctx.append(pg_conn)
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    log.info('API server started')


async def stop_server() -> None:
    await runner.cleanup()


import asyncio
asyncio.get_event_loop().run_until_complete(start_server())
asyncio.get_event_loop().run_forever()