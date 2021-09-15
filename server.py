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
        help="путь к папке с папками фотографий",
    )
    parser.add_argument(
        "--enable_logging",
        action="store_true",
        help="включить логирование",
    )
    parser.add_argument(
        "--sleep_sec",
        type=int,
        default=None,
        help="установить интервал между отправками фрагментов архива",
    )
    return parser


async def archivate(request):

    archive_hash = request.match_info["archive_hash"]

    if request.app["photo_folderpath"] in [".", ".."]:
        raise web.HTTPNotFound(text="Неверно указана директория с файлами на сервере")

    if not path.exists(f"./{ request.app['photo_folderpath'] }/{ archive_hash }"):
        raise web.HTTPNotFound(text="Архив не существует или был удален")

    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/html"
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename={ archive_hash }.zip"
    await response.prepare(request)
    zip_folderpath = f"{ request.app['photo_folderpath'] }/{ archive_hash }"
    proccess = await asyncio.create_subprocess_exec(
        "zip",
        "-r",
        "-",
        f"./{ zip_folderpath }",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            if proccess.stdout.at_eof():
                break
            file_data = await proccess.stdout.read(n=512000)
            await response.write(file_data)
            logging.warning("Sending archive chunk ...")
            await asyncio.sleep(request.app["sleep_sec"])

    except asyncio.exceptions.CancelledError:
        logging.warning("Stopping zip ...")
        proccess.kill()

    finally:
        logging.warning("Killing zip ...")
        proccess.kill()
        await proccess.communicate()
        logging.warning("Download was interrupted")

    return response


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


def main():
    env = Env()
    env.read_env()
    logging.basicConfig(encoding="utf-8", level=logging.DEBUG)
    app = web.Application()

    app["sleep_sec"] = env.int("SLEEP_SECS")
    app["photo_folderpath"] = env("PHOTOS_FOLDERPATH")

    env_enable_logging = env.bool("ENABLE_LOGGING")
    input_parser = create_input_parser()
    args = input_parser.parse_args()

    if not any([env_enable_logging, args.enable_logging]):
        logging.disable(logging.WARNING)

    if args.photos_folderpath:
        app["photo_folderpath"] = args.photos_folderpath

    if args.sleep_sec:
        app["sleep_sec"] = args.sleep_sec

    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archivate),
        ]
    )
    logging.info("Start server")
    web.run_app(app, port="8080")


if __name__ == "__main__":
    main()
