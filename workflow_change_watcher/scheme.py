import pathlib
from typing import List, Dict, Optional

from pydantic import BaseModel

from workflow_change_watcher.checksum_calculator import ChecksumCalculator


class File(BaseModel):
    relative_name: str
    checksum: str


class Lib(BaseModel):
    name: str
    files: List[File]


class Diff(BaseModel):
    file_checked: Optional[File]
    file_trusted: File


class FileRemoved(Diff):
    pass


class Diffs(BaseModel):
    diffs: List[Diff]

    def append(self, diff: Diff):
        self.diffs.append(diff)


class BaseChecksumStorage:
    libs: Dict[str, Lib] = {}

    def get_checksum_file_by_relative_filename(self, filename: str,
                                               lib_name: str):
        pass

    def generate_checksums(self, base_path: pathlib.Path, libs_names: List[str]) -> None:
        """
        Генерирует контрольные суммы библиотек
        :param base_path: Путь до папки, где лежат библиотеки
        :param libs_names: Список имён библиотек, которые нужно обработать
        """
        if not base_path.is_dir():
            raise RuntimeError("Должна быть папка")

        for dir_ in base_path.iterdir():
            if dir_.name in libs_names:
                self.libs[dir_.name] = (Lib(name=dir_.name, files=[]))
                for file in dir_.glob("**/*.py"):
                    with open(file, "rb") as f:
                        checksum = ChecksumCalculator.default_checksum(f)
                    new_file_checksum = File(relative_name=str(file.relative_to(base_path)),
                                             checksum=checksum)
                    self.libs[dir_.name].files.append(new_file_checksum)


class FileChecksumStorage(BaseChecksumStorage, BaseModel):
    trusted: bool = False

    def get_checksum_file_by_relative_filename(self, filename: str,
                                               lib_name: str) -> File:
        curr_lib = self.libs[lib_name]
        for file in curr_lib.files:
            if file.relative_name == filename:
                return file

    def compare(self, other: "FileChecksumStorage") -> Diffs:
        if not self.trusted:
            raise RuntimeError("Сравнивать можно только с файлами которым доверяем")
        diffs = Diffs(diffs=[])
        for lib_name, lib in self.libs.items():
            for file in lib.files:
                other_file = other.get_checksum_file_by_relative_filename(file.relative_name, lib_name)
                if other_file is None:
                    diffs.append(FileRemoved(file_checked=None, file_trusted=file))
                    continue
                if file.checksum != other_file.checksum:
                    diffs.append(Diff(file_checked=other_file, file_trusted=file))
        return diffs
