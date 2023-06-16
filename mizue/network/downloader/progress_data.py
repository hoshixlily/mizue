from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressData:
    downloaded: int
    filename: str
    filepath: str
    filesize: int
    percent: int
    finished: bool
    url: str
    uuid: str
