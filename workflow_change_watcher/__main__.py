import pathlib
import subprocess
import sys
from typing import List, Optional

from workflow_change_watcher import config
from workflow_change_watcher.args import configure_args_parser
from workflow_change_watcher.diff import get_diffs
from workflow_change_watcher.scheme import FileChecksumStorage
from workflow_change_watcher.utils import get_current_site_package_dir


def freeze_current_files_versions(freeze_path: pathlib.Path,
                                  trusted_path: pathlib.Path = None) -> None:
    """
    Записать контрольные суммы библиотек из доверенной папки в файл
    :param freeze_path: Путь до файла контрольных сумм
    :param trusted_path: Путь до доверенной папки с библиотеками
    """
    storage = FileChecksumStorage()
    storage.trusted = True
    storage.generate_checksums(trusted_path.resolve(), config.LIBS_TO_CHECK)
    json_txt = storage.model_dump_json()
    freeze_path.write_text(json_txt)


def fetch_trusted_files(trusted_path: pathlib.Path,
                        libs: List[str],
                        nexus_repo: Optional[str] = None) -> None:
    """
    Загружает из репозитория библиотеки в доверенную папку
    :param trusted_path:  Путь до доверенной папки
    :param libs: Список библиотек в формате как в requirements.txt
    :param nexus_repo: URL репозитория
    :return:
    """

    repo = ''
    if nexus_repo is not None:
        repo = f"-i {nexus_repo}"

    requirements = " ".join(libs)

    pip_install_command = ["py", '-m', 'pip',
                           "install", requirements,
                           "--target", str(trusted_path),
                           ]

    if repo:
        pip_install_command.append(repo)

    subprocess.check_call(pip_install_command,
                          stderr=sys.stdout,
                          stdout=sys.stdout
                          )


def main():
    args = configure_args_parser().parse_args()

    freeze_file = args.freeze_file or config.DEFAULT_FREEZE_FILE
    freeze_file_path = pathlib.Path(freeze_file)

    trusted_file = args.trusted_file or config.DEFAULT_TRUSTED_DIR
    trusted_path = pathlib.Path(trusted_file)

    if args.fetch_libs is not None:
        fetch_trusted_files(trusted_path, args.fetch_libs or config.LIBS_TO_CHECK, args.fetch_url)

    if args.freeze:
        freeze_current_files_versions(freeze_file_path, trusted_path)
        return

    need_to_check_dir = args.check_file or get_current_site_package_dir()
    need_to_check_dir_storage = FileChecksumStorage()
    need_to_check_dir_storage.generate_checksums(need_to_check_dir, config.LIBS_TO_CHECK)

    if freeze_file_path.exists():
        freeze_storage = FileChecksumStorage.model_validate_json(freeze_file_path.read_text())
        if not freeze_storage.trusted:
            raise RuntimeError(f"Файл {freeze_file} не доверенный")
        diffs = freeze_storage.compare(need_to_check_dir_storage)
        get_diffs(diffs, need_to_check_dir, trusted_path)

    else:
        trusted_checksum = FileChecksumStorage()
        trusted_checksum.generate_checksums(trusted_path, config.LIBS_TO_CHECK)
        trusted_checksum.trusted = True
        diffs = trusted_checksum.compare(need_to_check_dir_storage)
        get_diffs(diffs, need_to_check_dir, trusted_path)


if __name__ == '__main__':
    main()
