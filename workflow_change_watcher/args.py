import argparse


def configure_args_parser():
    arg_parser = argparse.ArgumentParser(
        prog="Workflow Change Watcher",
        description="Проверят изменились ли файлы в site-packages",
    )

    arg_parser.add_argument("--freeze-file",
                            dest="freeze_file",
                            help="Файл куда записать контрольные суммы библиотек",
                            type=str,
                            required=False,
                            nargs="?"
                            )

    arg_parser.add_argument("--freeze",
                            dest="freeze",
                            action="store_true",
                            help="Записать контрольные суммы библиотек из доверенной папки",
                            required=False)

    arg_parser.add_argument("--trusted",
                            "-t",
                            dest="trusted_file",
                            help="Папка, где находятся пакеты которым мы доверяем",
                            type=str,
                            required=False,
                            nargs="?"
                            )

    arg_parser.add_argument("--check",
                            "-c",
                            dest="check_file",
                            help="Папка, где находятся пакеты которые нужно проверить",
                            type=str,
                            required=False,
                            nargs="?"
                            )
    return arg_parser
