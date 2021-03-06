import re
from functools import partial
from pathlib import Path
from socket import gaierror

import aiohttp_jinja2
import asyncpg
import jinja2
from aiohttp import web

from utils import retry


@aiohttp_jinja2.template('index.jinja2')
async def index(request):
    count = await request.app['pool'].fetchval(
        'SELECT count(1) from html'
    )
    return {'count': count}


@aiohttp_jinja2.template('results.jinja2')
async def search(request):
    query = request.query.get('q')
    if not query:
        raise web.HTTPFound('/')
    result = await request.app['pool'].fetch(
        'SELECT hash, title, text, '
        'ts_rank_cd(tsv, query) AS rank '
        "FROM html, to_tsquery('jiebaqry', $1) query "
        'WHERE tsv @@ query '
        'ORDER BY rank DESC '
        'LIMIT 10',
        query
    )
    result = [
        {
            'hash': r['hash'],
            'title': highlight(r['title'], query),
            'text': highlight(r['text'], query)
        } for r in result
    ]
    return {'result': result, 'query': query}


WORDS = re.compile(r'\w+')


def highlight(s: str, query: str):
    for word in WORDS.findall(query):
        s = s.replace(word, f'<b>{word}</b>')
    return s


async def conn_pool(app):
    app['pool'] = await retry(
        partial(
            asyncpg.create_pool,
            host='db',
            user='postgres',
            database='ipfs_crawler'
        ),
        'database',
        gaierror, ConnectionRefusedError, asyncpg.CannotConnectNowError
    )
    yield
    await app['pool'].close()


app = web.Application()
aiohttp_jinja2.setup(
    app,
    loader=jinja2.PackageLoader('web', 'templates')
)
app.router.add_get('/', index)
app.router.add_get('/search', search)
static = Path(__file__).absolute().parent / 'static'
app.router.add_static('/static/', static)
app.cleanup_ctx.append(conn_pool)
web.run_app(app, port=9000)
