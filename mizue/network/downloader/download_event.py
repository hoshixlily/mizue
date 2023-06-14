from enum import Enum
from typing import TypedDict


class DownloadEvent(str, Enum):
    COMPLETED = "completed"
    """The download has been completed"""

    FAILED = "failed"
    """The download has been failed"""

    PROGRESS = "progress"
    """The download progress has been updated"""

    STARTED = "started"
    """The download has been started"""


class ProgressEventArgs(TypedDict):
    downloaded: int
    percent: int


class DownloadCompleteEventArgs(TypedDict):
    filename: str
    filepath: str
    filesize: int
    url: str


class DownloadFailureEventArgs(TypedDict):
    exception: Exception | None
    reason: str
    status_code: int | None
    url: str


class DownloadStartEventArgs(TypedDict):
    filename: str
    filepath: str
    filesize: int
    url: str
