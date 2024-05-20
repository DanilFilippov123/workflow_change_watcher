import logging
import pathlib
from typing import List, Dict, Optional

from pydantic import BaseModel

from workflow_change_watcher.checksum_calculator import ChecksumCalculator

logger = logging.getLogger(__name__)


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


class BaseChecksumStorage(BaseModel):
    libs: Dict[str, Lib] = {}

    def get_checksum_file_by_relative_filename(self, filename: str,
                                               lib_name: str):
        pass

    def compare(self, other: "BaseChecksumStorage") -> Diffs:
        pass


class FileChecksumStorage(BaseChecksumStorage):
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
