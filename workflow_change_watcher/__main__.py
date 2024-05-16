import difflib
import hashlib
import json
import pathlib
import sys

from typing import List, Dict, Set, Tuple, Optional
import argparse

from workflow_change_watcher import config


class FileChecksum:
    def __init__(self, file_name: pathlib.Path, absolute_path: Optional[pathlib.Path]):
        self.absolute_path = absolute_path
        self.file_path = file_name
        self._checksum = None

    def set_checksum(self, checksum):
        self._checksum = checksum

    def md5(self):
        if self._checksum is not None:
            return self._checksum
        hash_md5 = hashlib.md5()
        if self.absolute_path is None:
            raise RuntimeError("Неизвестный путь к файлу, возможно файл быть серииализован")
        with open(self.absolute_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self._checksum = hash_md5.hexdigest()
        return self._checksum

    def default_checksum(self):
        if self._checksum is not None:
            return self._checksum
        return self.md5()

    def __repr__(self):
        return f"{self.file_path.name=} {self.md5()=}"

    def __eq__(self, other: "FileChecksum"):
        if self._checksum is None:
            return (self.default_checksum() == other.default_checksum() and
                    self.file_path == self.file_path)
        return (self._checksum == other.default_checksum() and
                self.file_path == self.file_path)


class CompareError(Exception):
    pass


class DifferentDirs(CompareError):
    def __init__(self, lost_dirs: Set):
        self.lost_dirs = lost_dirs


class NewFileDetected(CompareError):
    def __init__(self, file):
        self.file = file


def make_path_relative_to_lib(p: pathlib.Path, lib_path: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(str(p.resolve()).split(lib_path.resolve().name)[1])


class ChecksumDir:
    def __init__(self, dir_path: pathlib.Path):
        self.__deserialized = False
        self.dir_path = dir_path
        self.founded_libs_dirs: Set[pathlib.Path] = set()

        self.files_per_libs: Dict[pathlib.Path, List[FileChecksum]] = {}

    def walk(self, files: List[str]):
        if not self.dir_path.is_dir():
            raise RuntimeError("Должна быть папка")
        for p in self.dir_path.iterdir():
            if p.name in files:
                relative_path = make_path_relative_to_lib(p, self.dir_path)
                self.founded_libs_dirs.add(
                    relative_path
                )
                self.files_per_libs[relative_path] = []
                # Рекурсивно проходим все файлы во всех подпапка .py
                for file in p.glob("**/*.py"):
                    self.files_per_libs[relative_path].append(
                        FileChecksum(make_path_relative_to_lib(file, self.dir_path), file))

    # TODO перепиши меня на пидантик
    def serialize(self, file=None):
        res = []
        for dir_name in self.files_per_libs:
            checksums_in_dir = {}
            for file_checksum in self.files_per_libs[dir_name]:
                checksums_in_dir[str(file_checksum.file_path).split(dir_name.name)[1]] = file_checksum.md5()
            res.append({dir_name.name: checksums_in_dir})

        print(json.dumps(res), file=file)

    def deserialize(self, json_text: str):
        obj = json.loads(json_text)
        lib: Dict[str, Dict[str, str]]
        for lib in obj:
            files_checksums: Dict[str, str]
            for dir_name, files_checksums in lib.items():
                dir_path = self.dir_path / pathlib.Path(dir_name)
                if not dir_path.exists():
                    raise RuntimeError("Пути не совместимы")
                self.founded_libs_dirs.add(dir_path)
                for file_name, checksum in files_checksums.items():
                    if dir_path not in self.files_per_libs:
                        self.files_per_libs[dir_path] = []
                    new_file_path = f"{dir_path}/{file_name}"
                    new_file_checksum = FileChecksum(pathlib.Path(new_file_path), None)
                    new_file_checksum.set_checksum(checksum)
                    self.files_per_libs[dir_path].append(new_file_checksum)

        self.__deserialized = True

    def __repr__(self):
        return f"ChecksumDir({self.dir_path=}, deserialized = {self.__deserialized})"

    def __eq__(self, other: "ChecksumDir"):
        # Проверяем что это чексумы одинаковых папок
        if self.founded_libs_dirs != other.founded_libs_dirs:
            return False
        for dir_name in self.files_per_libs:
            our_files = self.files_per_libs[dir_name]
            other_files = other.files_per_libs[dir_name]
            for file in our_files:
                if file not in other_files:
                    return False
        return True

    def compare(self, other: "ChecksumDir"):
        if self.founded_libs_dirs != other.founded_libs_dirs:
            # Возвращяем уникальные папки из обоих множеств
            raise DifferentDirs(self.founded_libs_dirs ^ other.founded_libs_dirs)

        different_files: List[Tuple[FileChecksum, FileChecksum]] = []

        for dir_name in self.files_per_libs:
            our_files = self.files_per_libs[dir_name]
            other_files = other.files_per_libs[dir_name]
            for file in our_files:
                curr_other_file = None
                for other_file in other_files:
                    if other_file.file_path == file.file_path:
                        curr_other_file = other_file
                        break
                if curr_other_file is None:
                    raise NewFileDetected(file)
                if file != curr_other_file:
                    different_files.append((file, curr_other_file))
        return different_files


def get_current_site_package_dir() -> pathlib.Path:
    for path in sys.path:
        if "venv" in path and "site-packages" in path:
            return pathlib.Path(path)


def freeze_current_files_versions(output_file_name: str):
    this_venv_site_packages = get_current_site_package_dir()
    checksums = ChecksumDir(this_venv_site_packages)
    checksums.walk(config.LIBS_TO_CHECK)
    with open(output_file_name, "w") as f:
        checksums.serialize(file=f)


def get_diffs(diffs: List[Tuple[FileChecksum, FileChecksum]],
              checked_lib: pathlib.Path,
              trusted_lib: pathlib.Path):

    for i in range(len(diffs)):
        first_file_path = pathlib.Path(f"{checked_lib}/{diffs[i][0].file_path}")
        second_file_path = pathlib.Path(f"{trusted_lib}/{diffs[i][1].file_path}")

        first_text: Optional[List[str]] = None
        second_text: Optional[List[str]] = None

        with open(first_file_path, "r") as f:
            first_text = f.readlines()
        with open(second_file_path, "r") as f:
            second_text = f.readlines()

        for diff in difflib.unified_diff(first_text, second_text, fromfile=str(first_file_path)):
            print(diff)


def main():
    arg_parser = argparse.ArgumentParser(
        prog="Workflow Change Watcher",
        description="Проверят изменились ли файлы в site-packages",
    )

    arg_parser.add_argument("--freeze",
                            action="store_true",
                            dest="freeze",
                            required=False,
                            )
    arg_parser.add_argument("freeze_file",
                            metavar="Файл куда записать чексуммы библиотек",
                            nargs="?")

    arg_parser.add_argument("--trusted",
                            "-t",
                            action="store_true",
                            dest="is_trusted_file",
                            required=False,
                            )
    arg_parser.add_argument("trusted_file",
                            metavar="Папка где находятся пакеты которым мы доверяем",
                            nargs="?")

    args = arg_parser.parse_args()

    freeze_file = args.freeze_file or config.DEFAULT_FREEZE_FILE

    if args.freeze:
        freeze_current_files_versions(freeze_file)
        return

    freeze_file_path = pathlib.Path(freeze_file)
    trusted_path = args.trusted_file if args.is_trusted_file else config.DEFAULT_TRUSTED_DIR
    trusted_path = pathlib.Path(trusted_path)

    need_to_check_dir = get_current_site_package_dir()
    need_to_check_dir_checksum = ChecksumDir(need_to_check_dir)
    need_to_check_dir_checksum.walk(config.LIBS_TO_CHECK)

    if freeze_file_path.exists():
        freeze_checksum = ChecksumDir(trusted_path)
        freeze_checksum.deserialize(freeze_file_path.read_text())
        diffs = need_to_check_dir_checksum.compare(freeze_checksum)
        get_diffs(diffs, need_to_check_dir, trusted_path)

    else:
        trusted_checksum = ChecksumDir(trusted_path)
        trusted_checksum.walk(config.LIBS_TO_CHECK)
        diffs = need_to_check_dir_checksum.compare(trusted_checksum)
        get_diffs(diffs, need_to_check_dir, trusted_path)


if __name__ == '__main__':
    main()
