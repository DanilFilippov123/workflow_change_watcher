import pathlib
import sys


def get_current_site_package_dir() -> pathlib.Path:
    """
    Возвращает папку с нынешними site-packages
    :return:
    """
    for path in sys.path:
        if "site-packages" in path:
            return pathlib.Path(path)