# Tiny stand-in for the `python-dotenv` package (no pip install required) -
# reads .env from the project root and copies any keys not already set in
# os.environ. Silently does nothing if the file doesn't exist.
import os
import pathlib


def load_env():
    root = pathlib.Path(__file__).resolve().parent.parent.parent
    env_path = root / '.env'
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)
