from aiohttp import web

from .globals import es

routes = web.RouteTableDef()
runner: web.AppRunner = None


@routes.get('/search/{query}')
async def search(request: web.Request) -> web.Response:
    result = await es.search(body={
        'query': {
            'match': {
                'content': request.match_info['query']
            }
        }
    })
    return web.json_response(result['hits'])


async def start_server() -> None:
    global runner
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()


async def stop_server() -> None:
    await runner.cleanup()
