from sanic import Sanic
from sanic.response import html, stream
import aiohttp
import asyncio

app = Sanic("PyPI Cache")


@app.route("/simple/")
@app.route("/simple/<package:string>/")
async def simple(request, package=""):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pypi.org/simple/{package}/") as response:
            html_ = await response.text()

    return html(
        html_.replace(
            '<a href="https://',
            '<a href="/package/https://',
        )
    )


async def download_in_background(uri, queue):
    async with aiohttp.ClientSession() as session:
        async with session.get(uri) as resp:
            await queue.put(resp)
            while batch := await resp.content.read(1024):
                await queue.put(batch)
            await queue.put("")


@app.route("/package/<uri:[^/].*?>")
async def package(request, uri):
    lock = asyncio.Lock()
    await lock.acquire()

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)