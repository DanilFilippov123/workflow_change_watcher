import hashlib
import logging
from typing import IO

logger = logging.getLogger(__name__)


class ChecksumCalculator:
    @staticmethod
    def default_checksum(file: IO):
        """
        По умолчанию вычисляется md5
        :param file: объект с read()
        :return: контрольную сумму файла
        """
        logger.debug(f"Вычисляем контрольную сумму по умолчанию для {file.name}")
        return ChecksumCalculator.md5(file)

    @staticmethod
    def md5(f: IO):
        logger.debug(f"Вычисляем контрольную сумму md5 для {f.name}")
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
        return hash_md5.hexdigest()
