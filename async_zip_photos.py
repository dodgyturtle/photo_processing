import asyncio
import time


async def archivate(foldername):
    proc = await asyncio.create_subprocess_shell(
        f"zip -r - { foldername }", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    while True:
        if proc.stdout.at_eof():
            break
        file_data = await proc.stdout.read(n=512000)
        write_archived_folder_to_file(file_data, "archive.zip")


def write_archived_folder_to_file(data, filename):
    with open(filename, "ab") as file:
        file.write(data)


def main():
    asyncio.run(archivate("photos/"))


if __name__ == "__main__":
    main()
