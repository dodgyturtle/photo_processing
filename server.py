import argparse
import asyncio
import logging
from os import path

import aiofiles
from aiohttp import web
from environs import Env


def create_input_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--photos_folderpath",
        type=str,
        default=None,
        help="Папка хранения фотографий",
    )
    parser.add_argument(
        "--enable_logging",
        action="store_true",
        help="Включить логирование",
    )
    parser.add_argument(
        "--sleep_sec",
        type=int,
        default=None,
        help="Время задержки между посылками пакетов",
    )
    return parser


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

    archive_hash = request.match_info.get("archive_hash")

    if PHOTOS_FOLDERPATH in [".", ".."]:
        raise web.HTTPNotFound(text="Неверно указана директория с файлами на сервере")

    if not path.exists(f"./{ PHOTOS_FOLDERPATH }/{ archive_hash }"):
        raise web.HTTPNotFound(text="Архив не существует или был удален")

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/html"
    response.headers["Content-Disposition"] = "inline"
    response.headers["Content-Disposition"] = "attachment"
    response.headers["Content-Disposition"] = f"attachment; filename={ archive_hash }.zip"
    await response.prepare(request)

    proccess = await asyncio.create_subprocess_shell(
        f"zip -r - { archive_hash }",
        cwd=rf"./{ PHOTOS_FOLDERPATH }",
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
            await asyncio.sleep(SLEEP_SECS)

    except asyncio.CancelledError:
        logging.warning("Stopping zip ...")
        await kill_all_proccesses(proccess.pid)
        raise

    finally:
        logging.warning("Killing zip ...")
        await kill_all_proccesses(proccess.pid)
        logging.warning("Download was interrupted")

    return response


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


def main():
    env = Env()
    env.read_env()

    global SLEEP_SECS
    global PHOTOS_FOLDERPATH

    SLEEP_SECS = env.int("SLEEP_SECS")
    PHOTOS_FOLDERPATH = env("PHOTOS_FOLDERPATH")

    env_enable_logging = env.bool("ENABLE_LOGGING")
    input_parser = create_input_parser()
    args = input_parser.parse_args()

    if not any([env_enable_logging, args.enable_logging]):
        logging.disable(logging.WARNING)

    if args.photos_folderpath:
        PHOTOS_FOLDERPATH = args.photos_folderpath

    if args.sleep_sec:
        SLEEP_SECS = args.sleep_sec

    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archivate),
        ]
    )
    logging.warning("Start server")
    web.run_app(app, port="80")


if __name__ == "__main__":
    main()
