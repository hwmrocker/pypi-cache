from __future__ import annotations

import asyncio
import re
import json
from typing import NamedTuple
from pathlib import Path

import aiohttp
from sanic import Sanic
from sanic.response import html
from sanic.response import stream


class CacheItem(NamedTuple):
    data: list[bytes]
    headers: dict[str, str]
    content_type: str


uri_re = re.compile(
    r'href="(?P<uri>https://[^"#]+)#(?P<hash>[^"]+)"(?P<other>[^>]*)>(?P<name>[^<]+)<'
)

app = Sanic("PyPI Cache")

local_cache: dict[str, CacheItem] = dict()
cachedir = Path("/home/olaf/pipcache")


def get_file_path(uri: str) -> str:
    return uri.split("/", 3)[-1]


def fix_line(line):
    if "<a href" not in line:
        return line
    uri, hash, other, name = uri_re.findall(line)[0]
    file_path = get_file_path(uri)
    proxy = "package"

    if file_path in local_cache:
        proxy = "cache"
    elif (cachedir / file_path).exists():
        proxy = "file"
    else:
        file_path = uri
    return f'<a href="/{proxy}/{file_path}#{hash}" {other}>{name}</a><br/>\n'


@app.route("/simple/")
@app.route("/simple/<package:string>/")
async def simple(request, package=""):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pypi.org/simple/{package}/") as response:
            html_ = await response.text()

    output = "\n".join(fix_line(line) for line in html_.splitlines())

    return html(output)


async def download_in_background(uri, queue):
    file_path = get_file_path(uri)

    async with aiohttp.ClientSession() as session:
        async with session.get(uri) as resp:
            cache_item = CacheItem(
                data=[],
                headers=dict((str(k), str(v)) for k, v in resp.headers.items()),
                content_type=resp.content_type,
            )
            local_cache[file_path] = cache_item
            await queue.put(resp)
            while batch := await resp.content.read(1024):
                cache_item.data.append(batch)
                await queue.put(batch)
            await queue.put("")

    metadatafile = cachedir / f"{file_path}.metadata"
    datafile = cachedir / file_path
    # tmpdatafile = cachedir / f"{file_path}.tmp"

    print(cache_item.headers)

    metadata = dict(
        headers=cache_item.headers,
        content_type=cache_item.content_type,
    )
    metadatafile.parent.mkdir(parents=True, exist_ok=True)
    metadatafile.write_text(json.dumps(metadata))
    await asyncio.sleep(0)

    datafile.parent.mkdir(parents=True, exist_ok=True)
    print(f"writing {datafile}")
    with datafile.open("wb") as fh:
        for batch in cache_item.data:
            fh.write(batch)
            await asyncio.sleep(0)
    print("done")
    # tmpdatafile.rename(datafile)


@app.route("/package/<uri:path>")
async def package(request, uri):
    queue = asyncio.Queue()
    asyncio.create_task(download_in_background(uri, queue))
    resp = await queue.get()

    async def stream_file(response):
        while batch := await queue.get():
            await response.write(batch)

    return stream(
        stream_file,
        status=resp.status,
        headers=resp.headers,
        content_type=resp.content_type,
    )


@app.route("/cache/<uri:path>")
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


@app.route("/file/<uri:path>")
async def file(request, uri):
    metadatafile = cachedir / f"{uri}.metadata"
    datafile = cachedir / uri

    metadata = json.load(metadatafile.open())

    cache_item = CacheItem(
        data=[], headers=metadata["headers"], content_type=metadata["content_type"]
    )
    local_cache[uri] = cache_item

    async def stream_file(response):
        with datafile.open("rb") as fh:
            while (batch := fh.read(1024)) :
                local_cache[uri].data.append(batch)
                await response.write(batch)

    return stream(
        stream_file,
        status=200,
        headers=local_cache[uri].headers,
        content_type=local_cache[uri].content_type,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
