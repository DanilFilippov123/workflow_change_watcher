import difflib
import logging
import pathlib

from workflow_change_watcher.scheme import FileRemoved, Diffs

logger = logging.getLogger(__name__)


def get_diffs(diffs: Diffs,
              checked_lib: pathlib.Path,
              trusted_lib: pathlib.Path):
    logger.debug(f"Выводим разницу между контрольной {checked_lib} и доверенной папками {trusted_lib}")
    for diff in diffs.diffs:
        if isinstance(diff, FileRemoved):
            print(f"Файл {diff.file_trusted.relative_name} был удален")
            continue

        logger.debug(f"Выводим разницу между {diff.file_checked.relative_name} и {diff.file_trusted.relative_name}")

        first_file_path = pathlib.Path(f"{checked_lib}/{diff.file_checked.relative_name}")
        second_file_path = pathlib.Path(f"{trusted_lib}/{diff.file_trusted.relative_name}")

        try:
            with open(first_file_path, "r", encoding="utf-8") as f:
                first_text = f.readlines()
            with open(second_file_path, "r", encoding="utf-8") as f:
                second_text = f.readlines()
        except UnicodeDecodeError:
            print(f"Файл {diff.file_checked.relative_name} не может быть прочитан")
            continue

        for text_diff in difflib.context_diff(second_text, first_text, fromfile=str(first_file_path)):
            print(text_diff)
