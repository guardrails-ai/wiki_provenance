import os
import subprocess
import sys


def install_chroma() -> bool:
    """Installs chromadb correctly based on the OS.

    Returns:
        bool: True if installation is successful, False otherwise.
    """

    try:
        if sys.platform in ("linux", "linux2"):
            # If on linux, install pysqlite3-binary and follow steps as mentioned here:
            # https://gist.github.com/defulmere/8b9695e415a44271061cc8e272f3c300
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pysqlite3-binary", "-q"]
            )
            __import__("pysqlite3")

            sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
            BASE_DIR = os.getcwd()

            DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
                }
            }
            print(DATABASES)

        # Install requirements
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "chromadb", "-q"]
        )
        return True
    except Exception:
        return False
