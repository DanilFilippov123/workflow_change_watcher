import os
import pathlib
import sys
import unittest
from typing import Optional

from workflow_change_watcher import config
from workflow_change_watcher.__main__ import fetch_trusted_files
from workflow_change_watcher.checksum_generator import FileChecksumGenerator
from workflow_change_watcher.scheme import FileChecksumStorage


class EasyChecksumTest(unittest.TestCase):
    trusted_dir = pathlib.Path("./test_data/trusted")
    check_dir = pathlib.Path("./test_data/check")
    test_data_dir = pathlib.Path("./test_data")

    # Путь к папке имя которой равно имени теста, создаётся в setUp
    current_trusted_lib_dir: Optional[pathlib.Path] = None
    current_check_lib_dir: Optional[pathlib.Path] = None

    @classmethod
    def setUpClass(cls):
        if not cls.trusted_dir.exists():
            print("Не существует папка с доверенными библиотеками")
            exit(1)
        if not cls.check_dir.exists():
            print("Не существует папка с проверяемыми библиотеками")
            exit(1)
        if not cls.test_data_dir.exists():
            print("Не существует папка с тестовыми данными")
            exit(1)

    def setUp(self):
        curr_test_name = self._testMethodName
        self.current_check_lib_dir = self.check_dir / curr_test_name
        self.current_trusted_lib_dir = self.trusted_dir / curr_test_name
        self.current_check_lib_dir.mkdir(exist_ok=True)
        self.current_trusted_lib_dir.mkdir(exist_ok=True)

    def test_compare_same_files(self):
        text = """
        def aboba():
            print("aboba")
        """

        trusted_file = self.current_trusted_lib_dir / "a.py"
        trusted_file.touch()
        check_file = self.current_check_lib_dir / "a.py"
        check_file.touch()

        check_file.write_text(text)
        trusted_file.write_text(text)

        checksum_generator = FileChecksumGenerator()
        trusted_checksum = checksum_generator.generate_checksum(self.trusted_dir,
                                                                ["test_compare_same_files"])

        trusted_checksum.trusted = True

        check_checksum = checksum_generator.generate_checksum(self.check_dir,
                                                              ["test_compare_same_files"])

        self.assertTrue(len(trusted_checksum.compare(check_checksum).diffs) == 0)


class HeavyChecksumTest(EasyChecksumTest):

    def setUp(self):
        pass

    @classmethod
    def setUpClass(cls):
        """
        Скачиваем доверенные файлы в доверенную папку и проверяемую папку
        :return:
        """
        prev_stdin = sys.stdin
        prev_stdout = sys.stdout
        prev_stderr = sys.stderr

        sys.stderr = os.fdopen(2, ' w')
        sys.stdout = os.fdopen(1, 'w')
        sys.stdin = os.fdopen(0, 'r')

        try:
            fetch_trusted_files(cls.trusted_dir, config.LIBS_TO_CHECK, config.NEXUS_REPO)
            fetch_trusted_files(cls.check_dir, config.LIBS_TO_CHECK, config.NEXUS_REPO)
        finally:
            sys.stdout = prev_stdout
            sys.stdin = prev_stdin
            sys.stderr = prev_stderr

    def test_compare_same_files(self):
        checksum_generator = FileChecksumGenerator()
        trusted_checksum = checksum_generator.generate_checksum(self.trusted_dir,
                                                                ["test_compare_same_files"])

        trusted_checksum.trusted = True

        check_checksum = checksum_generator.generate_checksum(self.check_dir,
                                                              ["test_compare_same_files"])

        self.assertTrue(len(trusted_checksum.compare(check_checksum).diffs) == 0)
