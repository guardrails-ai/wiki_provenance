import subprocess
import sys


def install_chroma():
    """Installs chromadb correctly based on the OS.

    Returns:
        bool: True if installation is successful, False otherwise.
    """

    try:
        if sys.platform in ("linux", "linux2"):
            # If on linux, install pysqlite3-binary and follow steps as mentioned here:
            # https://gist.github.com/defulmere/8b9695e415a44271061cc8e272f3c300
            print("Installing `pysqlite3-binary`...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pysqlite3-binary"]
            )
            __import__("pysqlite3")
            sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

        # Install chromadb
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "chromadb", "-q"]
        )
        print("Successfully installed `chromadb`.")
    except Exception as e:
        raise RuntimeError(f"Failed to install `chromadb`:\n{e}") from e
