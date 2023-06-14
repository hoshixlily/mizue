import os
import time
import urllib.parse
from collections.abc import Callable
from typing import TypedDict

import pathvalidate
import requests
import uuid

from mizue.file import FileUtils
from mizue.network.downloader import DownloadEvent, ProgressEventArgs
from mizue.network.downloader.download_event import DownloadFailureEventArgs, DownloadStartEventArgs, \
    DownloadCompleteEventArgs
from mizue.printer import Printer
from mizue.progress import Progress
from mizue.util import EventListener


class DownloadMetadata(TypedDict):
    filename: str
    filepath: str
    filesize: int
    url: str
    uuid: str


class ProgressData(TypedDict):
    downloaded: int
    filename: str
    filepath: str
    filesize: int
    percent: int
    finished: bool
    url: str
    uuid: str


class DownloaderTool(EventListener):
    def __init__(self):
        self.no_progress = False
        """True to disable progress bar output"""

        self.output_path = ".."
        """The output path for the downloaded files"""

        self.retry_count = 1
        """The number of times to retry the download if it fails"""

        self.parallel_downloads = 5
        """The number of parallel downloads"""

        self.timeout = 10
        """The timeout in seconds for the connection"""

        self.verbose = True
        """True to enable verbose output"""

    def download(self, url: str, output_path: str = None):
        path_to_save = output_path if output_path is not None and len(output_path) > 0 else self.output_path
        response = self._get_response(url)
        progress = Progress(0, 0, 0, 10)  # IMPORTANT: Max value should be set to the file size inside _progress_init

        if response and response.status_code == 200:
            metadata = self._get_download_metadata(response, path_to_save)
            self._download(response, metadata, path_to_save, lambda init_data: self._progress_init(init_data, progress),
                           lambda progress_data: self._progress_callback(progress_data, progress))
        else:
            self._fire_failure_event(url, response, exception=None)

    def _download(self, response: requests.Response, metadata: DownloadMetadata, output_path: str = None,
                  progress_init: Callable[[DownloadMetadata], None] = None,
                  progress_callback: Callable[[ProgressData], None] = None):
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        if progress_init:
            progress_init(metadata)
        try:
            with open(metadata["filepath"], 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    response.raw.decode_content = True
                    chunk_size = len(chunk)
                    f.write(chunk)
                    downloaded += chunk_size
                    percent = int((downloaded / metadata["filesize"]) * 100)
                    if progress_callback:
                        progress_data: ProgressData = {
                            "downloaded": downloaded,
                            "filename": metadata["filename"],
                            "filepath": metadata["filepath"],
                            "filesize": metadata["filesize"],
                            "percent": percent,
                            "finished": False,
                            "url": metadata["url"],
                            "uuid": metadata["uuid"]
                        }
                        progress_callback(progress_data)
                if progress_callback:
                    progress_data: ProgressData = {
                        "downloaded": downloaded,
                        "filename": metadata["filename"],
                        "filepath": metadata["filepath"],
                        "filesize": metadata["filesize"],
                        "percent": 100,
                        "finished": True,
                        "url": metadata["url"],
                        "uuid": metadata["uuid"]
                    }
                    progress_callback(progress_data)
        except Exception as e:
            self._fire_failure_event(metadata["url"], response, exception=e)

    def _fire_failure_event(self, url: str, response: requests.Response, exception: Exception | None):
        self._fire_event(DownloadEvent.FAILED, DownloadFailureEventArgs(
            url=url,
            status_code=response.status_code if response else -1,
            reason=response.reason if response else "Unknown",
            exception=exception
        ))

    def _get_download_metadata(self, response: requests.Response, output_path: str) -> DownloadMetadata:
        filename = self._get_filename(response)
        filepath = os.path.join(output_path, filename)
        filesize = int(response.headers["Content-Length"] if "Content-Length" in response.headers.keys() else 1)
        return {
            "filename": filename,
            "filepath": filepath,
            "filesize": filesize,
            "url": response.url,
            "uuid": str(uuid.uuid4())
        }

    @staticmethod
    def _get_filename(response: requests.Response) -> str | None:
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            filename = content_disposition.split("filename=")[1].split(";")[0].replace("\"", "").strip()
            if filename:
                return filename
        else:
            unquoted_filename = urllib.parse.unquote(response.url.split("/")[-1], encoding='utf-8', errors='replace')
            if unquoted_filename and "?" in unquoted_filename:
                unquoted_filename = unquoted_filename[:unquoted_filename.rfind("?")]
            if unquoted_filename:
                return pathvalidate.sanitize_filename(unquoted_filename)
        return None

    def _get_response(self, url: str) -> requests.Response | None:
        fetching = True
        fetch_try_count = 0
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        }

        response: requests.Response | None = None
        while fetching:
            try:
                response = requests.get(url, stream=True, timeout=self.timeout, headers=headers)
                fetching = False
            except requests.exceptions.Timeout as e:
                fetch_try_count += 1
                if fetch_try_count > self.retry_count:
                    fetching = False
                    self._fire_failure_event(url, response, e)
                continue
            except requests.exceptions.RequestException as e:
                fetching = False
                self._fire_failure_event(url, response, e)
                continue
        return response

    def _progress_callback(self, data: ProgressData, progress: Progress):
        if not self.no_progress:
            info = f'[{FileUtils.get_readable_file_size(data["downloaded"])}/{FileUtils.get_readable_file_size(data["filesize"])}]'
            progress.update_value(data["downloaded"])
            progress.set_info(info)
        self._fire_event(DownloadEvent.PROGRESS,
                         ProgressEventArgs(downloaded=data["downloaded"], percent=data["percent"]))

        if data["finished"]:
            if not self.no_progress:
                info = f'[{FileUtils.get_readable_file_size(data["filesize"])}]'
                progress.update_value(data["filesize"])
                progress.set_info(info)
                time.sleep(1)
                progress.stop()
            self._fire_event(DownloadEvent.COMPLETED, DownloadCompleteEventArgs(
                url=data["url"],
                filename=data["filename"],
                filepath=data["filepath"],
                filesize=data["filesize"],
            ))

    def _progress_init(self, data: DownloadMetadata, progress: Progress):
        if not self.no_progress:
            progress.set_end_value(data["filesize"])
            progress.start()
        self._fire_event(DownloadEvent.STARTED, DownloadStartEventArgs(
            url=data["url"],
            filename=data["filename"],
            filepath=data["filepath"],
            filesize=data["filesize"],
        ))
