from enum import Enum
from typing import TypedDict


class DownloadEvent(str, Enum):
    COMPLETED = "completed"
    """The progress has been completed"""

    PROGRESS = "progress"
    """The progress has been updated"""

    STARTED = "started"
    """The progress has been started"""


class ProgressEventArgs(TypedDict):
    downloaded: int
    percent: int
