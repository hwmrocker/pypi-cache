from __future__ import annotations
from sanic import Sanic
from sanic.response import html, stream
import aiohttp
import asyncio
from typing import NamedTuple
import re

uri_re = re.compile(r'https://[^"#]+')
app = Sanic("PyPI Cache")

local_cache = dict()


def fix_line(line):
    if "<a href" not in line:
        return line
    # print(repr(line))
    uri = uri_re.findall(line)[0]
    package_or_cache = "cache" if uri in local_cache else "package"
    return line.replace(
        '<a href="https://',
        f'<a href="/{package_or_cache}/https://',
    )


@app.route("/simple/")
@app.route("/simple/<package:string>/")
async def simple(request, package=""):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pypi.org/simple/{package}/") as response:
            html_ = await response.text()

    output = "\n".join(fix_line(line) for line in html_.splitlines())

    return html(output)


async def download_in_background(uri, queue):
    async with aiohttp.ClientSession() as session:
        async with session.get(uri) as resp:
            await queue.put(resp)
            while batch := await resp.content.read(1024):
                await queue.put(batch)
            await queue.put("")


class CacheItem(NamedTuple):
    data: list[bytes]
    headers: dict[str, str]
    content_type: str


@app.route("/package/<uri:[^/].*?>")
async def package(request, uri):
    queue = asyncio.Queue()
    asyncio.create_task(download_in_background(uri, queue))
    resp = await queue.get()

    cache_item = CacheItem(
        data=[], headers=resp.headers, content_type=resp.content_type
    )
    local_cache[uri] = cache_item

    async def stream_file(response):
        while batch := await queue.get():
            local_cache[uri].data.append(batch)
            await response.write(batch)

    return stream(
        stream_file,
        status=resp.status,
        headers=resp.headers,
        content_type=resp.content_type,
    )


@app.route("/cache/<uri:[^/].*?>")
async def cache(request, uri):
    async def stream_file(response):
        for batch in local_cache[uri].data:
            await response.write(batch)

    return stream(
        stream_file,
        status=200,
        headers=local_cache[uri].headers,
        content_type=local_cache[uri].content_type,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)