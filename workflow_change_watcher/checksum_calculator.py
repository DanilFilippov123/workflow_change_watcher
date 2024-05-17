import hashlib


class ChecksumCalculator:
    @staticmethod
    def default_checksum(file):
        """
        По умолчанию вычисляется md5
        :param file: объект с read()
        :return: контрольную сумму файла
        """
        return ChecksumCalculator.md5(file)

    @staticmethod
    def md5(f):
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
        return hash_md5.hexdigest()
