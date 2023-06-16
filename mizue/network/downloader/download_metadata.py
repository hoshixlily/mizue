from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadMetadata:
    filename: str
    filepath: str
    filesize: int
    url: str
    uuid: str
