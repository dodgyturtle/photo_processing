import asyncio
import logging
from os import path

import aiofiles
from aiohttp import web


INTERVAL_SECS = 1


async def kill_all_proccesses(pid):
    procces = await asyncio.create_subprocess_shell(
        f"pgrep -P { pid }",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await procces.communicate()
    subprocces_pid = stdout.decode()
    if subprocces_pid:
        await asyncio.create_subprocess_shell(f"kill -9 { subprocces_pid }", stdout=None, stderr=None)
        return
    await asyncio.create_subprocess_shell(f"kill -9 { pid }", stdout=None, stderr=None)


async def archivate(request):
    directoryname = "test_photos"
    archive_hash = request.match_info.get("archive_hash")

    if directoryname in [".", ".."]:
        raise web.HTTPNotFound(text="Неверно указана директория с файлами на сервере")

    if not path.exists(f"./{ directoryname }/{ archive_hash }"):
        raise web.HTTPNotFound(text="Архив не существует или был удален")

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/html"
    response.headers["Content-Disposition"] = "inline"
    response.headers["Content-Disposition"] = "attachment"
    response.headers["Content-Disposition"] = f"attachment; filename={ archive_hash }.zip"
    await response.prepare(request)

    proccess = await asyncio.create_subprocess_shell(
        f"zip -r - { archive_hash }",
        cwd=rf"./{ directoryname }",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            if proccess.stdout.at_eof():
                break
            file_data = await proccess.stdout.read(n=512000)
            logging.warning("Sending archive chunk ...")

            await response.write(file_data)
            await asyncio.sleep(3)

    except asyncio.CancelledError:
        logging.warning("Stopping zip ...")
        await kill_all_proccesses(proccess.pid)
        raise

    finally:
        await kill_all_proccesses(proccess.pid)
        logging.warning("Stopping zip ...")
        logging.warning("Download was interrupted")

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
    web.run_app(app, port="80")
