import logging

from aiohttp import web

from .globals import es

routes = web.RouteTableDef()
runner: web.AppRunner = None
log = logging.getLogger(__name__)


@routes.get('/search/{query}')
async def search(request: web.Request) -> web.Response:
    result = await es.search(body={
        'query': {
            'match': {
                'text': request.match_info['query']
            }
        },
        'highlight': {
            'fields': {
                'text': {}
            }
        }
    })
    return web.json_response(
        result['hits'],
        headers={'Access-Control-Allow-Origin': '*'}
    )


async def start_server() -> None:
    global runner
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    log.info('API server started')


async def stop_server() -> None:
    await runner.cleanup()
