import asyncio
import datetime

import aiofiles
from aiohttp import web

INTERVAL_SECS = 1


async def archivate(request):
    archive_hash = request.match_info.get("archive_hash")
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/html"
    response.headers["Content-Disposition"] = "inline"
    response.headers["Content-Disposition"] = "attachment"
    response.headers["Content-Disposition"] = f"attachment; filename={ archive_hash }.zip"
    await response.prepare(request)

    proccess = await asyncio.create_subprocess_shell(
        f"zip -r - { archive_hash }",
        cwd=r"./test_photos",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    while True:
        if proccess.stdout.at_eof():
            break
        file_data = await proccess.stdout.read(n=512000)
        await response.write(file_data)
    return response


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archivate),
        ]
    )
    web.run_app(app)
