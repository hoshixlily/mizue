from enum import Enum
from dataclasses import dataclass
from typing import Optional


class DownloadEventType(str, Enum):
    COMPLETED = "completed"
    """The download has been completed"""

    FAILED = "failed"
    """The download has been failed"""

    PROGRESS = "progress"
    """The download progress has been updated"""

    STARTED = "started"
    """The download has been started"""


@dataclass(frozen=True)
class DownloadBaseEvent:
    filename: str
    filepath: str
    url: str


@dataclass(frozen=True)
class ProgressEventArgs(DownloadBaseEvent):
    downloaded: int
    filesize: int
    percent: int


@dataclass(frozen=True)
class DownloadCompleteEvent(DownloadBaseEvent):
    filesize: int


@dataclass(frozen=True)
class DownloadFailureEvent:
    exception: BaseException | None
    filepath: Optional[str]
    reason: str
    status_code: int | None
    url: str


@dataclass(frozen=True)
class DownloadStartEvent(DownloadBaseEvent):
    filesize: int
