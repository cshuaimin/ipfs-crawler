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
        'SELECT hash, '
        "ts_headline('jiebacfg', title, query) AS title, "
        "ts_headline('jiebacfg', text, query) AS text, "
        'ts_rank_cd(tsv, query) AS rank '
        "FROM crawler_html, to_tsquery('jiebacfg', $1) query "
        'WHERE tsv @@ query '
        'ORDER BY rank DESC '
        'LIMIT 10',
        query
    )
    r0 = dict(result[0])
    r1 = dict(result[1])
    print(r0['title'], r0['rank'])
    print(r1['title'], r1['rank'])
    return {'result': result}


app = web.Application()
aiohttp_jinja2.setup(
    app,
    loader=jinja2.PackageLoader('webui', 'templates')
)
app.router.add_get('/', index)
app.router.add_get('/search', search)
app.router.add_static('/static/', '/home/csm/code/ipfs_crawler/webui/static')
async def conn_pool(app):
    app['pool'] = await asyncpg.create_pool(user='postgres', database='ipfs_crawler')
    yield
    await app['pool'].close()
app.cleanup_ctx.append(conn_pool)
web.run_app(app)

