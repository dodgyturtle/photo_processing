from subprocess import Popen, PIPE


def archive_folder(foldername):
    process = Popen(["zip", "-r", "-", foldername], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    return stdout


def write_archived_folder_to_file(data, filename):
    with open(filename, "wb") as file:
        file.write(data)


def main():
    archived_folder = archive_folder("photos")
    write_archived_folder_to_file(archived_folder, "archive.zip")


if __name__ == "__main__":
    main()
