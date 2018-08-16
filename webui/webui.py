import aiohttp_jinja2
import jinja2
import asyncpg
from aiohttp import web


@aiohttp_jinja2.template('index.jinja2')
def index(request):
    return {}


@aiohttp_jinja2.template('results.jinja2')
async def search(request):
    query = request.query.get('q')
    if not query:
        raise web.HTTPFound('/')
    result = await request.app['pool'].fetch(
        'SELECT hash, title, text, '
        'ts_rank_cd(tsv, query) AS rank '
        "FROM crawler_html, to_tsquery('jiebacfg', $1) query "
        'WHERE tsv @@ query '
        'ORDER BY rank DESC '
        'LIMIT 10',
        query
    )
    return {'result': result}


app = web.Application()
aiohttp_jinja2.setup(
    app,
    loader=jinja2.PackageLoader('webui', 'templates')
)
app.router.add_get('/', index)
app.router.add_get('/search', search)
app.router.add_static('/static/', 'webui/static')
async def conn_pool(app):
    app['pool'] = await asyncpg.create_pool(user='postgres', database='ipfs_crawler')
    yield
    await app['pool'].close()
app.cleanup_ctx.append(conn_pool)
web.run_app(app, port=80)