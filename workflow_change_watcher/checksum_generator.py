import pathlib
from typing import List

from workflow_change_watcher.checksum_calculator import ChecksumCalculator
from workflow_change_watcher.scheme import BaseChecksumStorage, FileChecksumStorage, Lib, File


class BaseChecksumGenerator:
    def generate_checksum(self, base_path: pathlib.Path, libs_names: List[str]) -> BaseChecksumStorage:
        pass


class FileChecksumGenerator(BaseChecksumGenerator):
    def generate_checksums(self, base_path: pathlib.Path, libs_names: List[str]) -> FileChecksumStorage:
        """
        Генерирует контрольные суммы библиотек
        :param base_path: Путь до папки, где лежат библиотеки
        :param libs_names: Список имён библиотек, которые нужно обработать
        """
        if not base_path.is_dir():
            raise RuntimeError("Должна быть папка")

        res = FileChecksumStorage()

        for dir_ in base_path.iterdir():
            if dir_.name in libs_names:
                res.libs[dir_.name] = (Lib(name=dir_.name, files=[]))
                for file in dir_.glob("**/*.py"):
                    with open(file, "rb") as f:
                        checksum = ChecksumCalculator.default_checksum(f)
                    new_file_checksum = File(relative_name=str(file.relative_to(base_path)),
                                             checksum=checksum)
                    res.libs[dir_.name].files.append(new_file_checksum)

        return res
