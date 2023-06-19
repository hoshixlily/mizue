import os
import urllib.parse
import uuid
from typing import Callable

import requests
from pathvalidate import sanitize_filename

from mizue.util import EventListener
from .download_event import DownloadEventType, DownloadFailureEvent, DownloadCompleteEvent, DownloadStartEvent, \
    ProgressEventArgs
from .download_metadata import DownloadMetadata
from .progress_data import ProgressData


class Downloader(EventListener):
    def __init__(self):
        super().__init__()
        self._alive = True

        self.output_path = "."
        """The output path for the downloaded files"""

        self.retry_count = 5
        """The number of times to retry the download if it fails"""

        self.timeout = 10
        """The timeout in seconds for the connection"""

    def close(self):
        """
        Closes the downloader. This will stop any ongoing downloads.

        In order to download again, a new instance of the downloader must be created,
        or the open() method must be called.
        """
        self._alive = False

    def download(self, url: str, output_path: str = None):
        path_to_save = output_path if output_path is not None and len(output_path) > 0 else self.output_path

        response = self._get_response(url)
        if response and response.status_code == 200:
            metadata = self._get_download_metadata(response, path_to_save)
            self._download(response, metadata, path_to_save, lambda init_data: self._progress_init(init_data),
                           lambda progress_data: self._progress_callback(progress_data))
        else:
            self._fire_failure_event(url, response, exception=None)

    def open(self):
        """
        Opens the downloader. This will allow downloads to be performed once again.
        Use this method if the downloader has been closed via the close() method.
        """
        self._alive = True

    def _download(self, response: requests.Response, metadata: DownloadMetadata, output_path: str = None,
                  progress_init: Callable[[DownloadMetadata], None] = None,
                  progress_callback: Callable[[ProgressData], None] = None):
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        if progress_init:
            progress_init(metadata)
        try:
            with open(metadata.filepath, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=1024):
                    if not self._alive:
                        break
                    response.raw.decode_content = True
                    chunk_size = len(chunk)
                    f.write(chunk)
                    downloaded += chunk_size
                    percent = int((downloaded / metadata.filesize) * 100)
                    if progress_callback:
                        progress_data = ProgressData(
                            downloaded=downloaded,
                            filename=metadata.filename,
                            filepath=metadata.filepath,
                            filesize=metadata.filesize,
                            percent=percent,
                            finished=False,
                            url=metadata.url,
                            uuid=metadata.uuid
                        )
                        progress_callback(progress_data)
                if self._alive:
                    if progress_callback:
                        progress_data = ProgressData(
                            downloaded=downloaded,
                            filename=metadata.filename,
                            filepath=metadata.filepath,
                            filesize=metadata.filesize,
                            percent=100,
                            finished=True,
                            url=metadata.url,
                            uuid=metadata.uuid
                        )
                        progress_callback(progress_data)
                else:
                    f.close()
                    os.remove(metadata.filepath)
                    self._fire_failure_event(metadata.url, response, exception=Exception("Download cancelled"),
                                             filepath=metadata.filepath)
        except Exception as e:
            self._fire_failure_event(metadata.url, response, exception=e, filepath=metadata.filepath)
            raise e

    def _fire_failure_event(self, url: str, response: requests.Response, exception: BaseException | None,
                            filepath: str = None):
        self._fire_event(DownloadEventType.FAILED, DownloadFailureEvent(
            url=url,
            status_code=response.status_code if response else -1,
            reason=response.reason if response else "Unknown",
            exception=exception,
            filepath=filepath,
        ))

    def _get_download_metadata(self, response: requests.Response, output_path: str) -> DownloadMetadata:
        filename = self._get_filename(response)
        filepath = os.path.join(output_path, filename)
        filesize = int(response.headers["Content-Length"] if "Content-Length" in response.headers.keys() else 1)
        return DownloadMetadata(
            filename=filename,
            filepath=filepath,
            filesize=filesize,
            url=response.url,
            uuid=str(uuid.uuid4())
        )

    @staticmethod
    def _get_filename(response: requests.Response) -> str | None:
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            filename = content_disposition.split("filename=")[1].split(";")[0].replace("\"", "").strip()
            if filename:
                return filename
        else:
            unquoted_url = urllib.parse.unquote_plus(response.url, encoding='utf-8', errors='replace')
            unquoted_url = unquoted_url.replace("?", "_")
            url_filename = urllib.parse.urlparse(unquoted_url)
            filename = os.path.basename(url_filename.path)
            if filename:
                return sanitize_filename(filename)
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

    def _progress_callback(self, data: ProgressData):
        self._fire_event(DownloadEventType.PROGRESS, ProgressEventArgs(
            downloaded=data.downloaded,
            percent=data.percent,
            filename=data.filename,
            filepath=data.filepath,
            filesize=data.filesize,
            url=data.url,
        ))

        if data.finished:
            self._fire_event(DownloadEventType.COMPLETED, DownloadCompleteEvent(
                url=data.url,
                filename=data.filename,
                filepath=data.filepath,
                filesize=data.filesize,
            ))

    def _progress_init(self, data: DownloadMetadata):
        self._fire_event(DownloadEventType.STARTED, DownloadStartEvent(
            url=data.url,
            filename=data.filename,
            filepath=data.filepath,
            filesize=data.filesize,
        ))
