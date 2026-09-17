"""Stream a ZIP of regular files and directories to stdout inside the Linux guest."""
import os
from pathlib import PurePosixPath
import shutil
import stat
import sys
import zipfile


def export_zip(source, output):
    # Pin directories and refuse symlinks, including when entries change while
    # exporting. Never open a special file that could block the exporter.
    root_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            def fail(error):
                raise error

            for directory, dirs, files, dir_fd in os.fwalk(
                    ".", dir_fd=root_fd, follow_symlinks=False, onerror=fail):
                for name in sorted(dirs + files):
                    path = (PurePosixPath(directory) / name).as_posix()
                    mode = os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode
                    if stat.S_ISDIR(mode):
                        archive.writestr(path + "/", b"")
                    elif stat.S_ISREG(mode):
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                     dir_fd=dir_fd)
                        with os.fdopen(fd, "rb") as stream:
                            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                                raise ValueError(f"ZIP export requires a regular file: {path}")
                            with archive.open(path, "w", force_zip64=True) as member:
                                shutil.copyfileobj(stream, member)
                    else:
                        raise ValueError(f"ZIP export refuses links and special files: {path}")
    finally:
        os.close(root_fd)


if __name__ == "__main__":
    export_zip(sys.argv[1], sys.stdout.buffer)
