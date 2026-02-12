import datetime
import sys

class Logger:
    @staticmethod
    def _get_timestamp():
        return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def info(message: str):
        print(f"[INFO] {Logger._get_timestamp()} - {message}", flush=True)

    @staticmethod
    def warn(message: str):
        print(f"[WARN] {Logger._get_timestamp()} - {message}", flush=True)

    @staticmethod
    def error(message: str):
        print(f"[ERROR] {Logger._get_timestamp()} - {message}", file=sys.stderr, flush=True)

logger = Logger