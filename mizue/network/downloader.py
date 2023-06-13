import os.path
import time
import urllib.parse
import uuid
from collections.abc import Callable
from multiprocessing.pool import ThreadPool
from typing import TypedDict

import pathvalidate
import requests

from mizue.file import FileUtils
from mizue.printer import Printer, TablePrinter, BorderStyle, Alignment
from mizue.progress import Progress


class DownloadMetadata(TypedDict):
    filename: str
    filepath: str
    filesize: int
    url: str
    uuid: str


class ProgressData(TypedDict):
    downloaded: int
    filesize: int
    percent: int
    finished: bool
    uuid: str


class Downloader:
    def __init__(self):
        self.output_path = "."
        """The output path for the downloaded files"""

        self.retry_count = 1
        """The number of times to retry the download if it fails"""

        self.parallel_downloads = 5
        """The number of parallel downloads"""

        self.silent = False
        """True to disable all output. If verbose is enabled, this will be ignored."""

        self.timeout = 10
        """The timeout in seconds for the connection"""

        self.verbose = True
        """True to enable verbose output"""

    def download(self, url: str, output_path: str = None):
        self.output_path = output_path or self.output_path

        if self.verbose:
            Printer.info(f'Downloading {url} to {output_path}')
            Printer.info(f'Connecting to {url}...')

        response = self._get_response(url)
        progress = Progress(0, 100, 0, 10)

        if response and response.status_code == 200:
            metadata = self._get_download_metadata(response)
            self._download(response, metadata, output_path, lambda init_data: self._progress_init(init_data, progress),
                           lambda progress_data: self._progress_callback(progress_data, progress))
        else:
            if not self.silent:
                Printer.error(f'Error while downloading: {response.status_code}')

    def _get_response(self, url: str) -> requests.Response | None:
        fetching = True
        fetch_try_count = 0
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        }

        response: requests.Response | None = None
        while fetching:
            try:
                response = requests.get(url, timeout=self.timeout, headers=headers)
                fetching = False
            except requests.exceptions.Timeout as e:
                # if not self.silent:
                #     Printer.error(f'Connection timed out: {e}')
                fetch_try_count += 1
                if fetch_try_count > self.retry_count:
                    fetching = False
                continue
        return response

    @staticmethod
    def _progress_callback(data: ProgressData, progress: Progress):
        info = f'{data["percent"]}% [{FileUtils.get_readable_file_size(data["downloaded"])}/{FileUtils.get_readable_file_size(data["filesize"])}]'
        progress.update_value(data["percent"])
        progress.set_info(info)
        if data["finished"]:
            progress.stop()

    @staticmethod
    def _progress_init(data: DownloadMetadata, progress: Progress):
        Printer.info(f'Downloading {data["filename"]} ({FileUtils.get_readable_file_size(data["filesize"])})')
        progress.start()

    @staticmethod
    def _download(response: requests.Response, metadata: DownloadMetadata, output_path: str = None,
                  progress_init: Callable[[DownloadMetadata], None] = None,
                  progress_callback: Callable[[ProgressData], None] = None):
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        if progress_init:
            progress_init(metadata)
        try:
            with open(metadata["filepath"], 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=1024):
                    response.raw.decode_content = True
                    chunk_size = len(chunk)
                    f.write(chunk)
                    downloaded += chunk_size
                    percent = int((downloaded / metadata["filesize"]) * 100)
                    if progress_callback:
                        progress_data: ProgressData = {
                            "downloaded": downloaded,
                            "filesize": metadata["filesize"],
                            "percent": percent,
                            "finished": False,
                            "uuid": metadata["uuid"]
                        }
                        progress_callback(progress_data)
                if progress_callback:
                    progress_data: ProgressData = {
                        "downloaded": downloaded,
                        "filesize": metadata["filesize"],
                        "percent": 100,
                        "finished": True,
                        "uuid": metadata["uuid"]
                    }
                    progress_callback(progress_data)
        except Exception as e:
            raise e

    def download_list(self, urls: list[str], output_path: str = None):
        distinct_urls = list(set(urls))

        if self.verbose:
            Printer.info(f'Found {len(distinct_urls)} files to download.')
            Printer.info(f'Gathering download metadata...')

        response_list = self._get_responses(distinct_urls)
        responses = [r for r in response_list if r.status_code == 200]
        failed_responses = [r for r in response_list if r.status_code == 404]
        if response_list:
            if self.verbose:
                Printer.success(f'Found {len(responses)} files to download. ({len(failed_responses)} failed)')
                Printer.info(f'Gathering download metadata...')

            metadata_pool = ThreadPool(self.parallel_downloads)
            metadata_list = metadata_pool.starmap(self._get_download_metadata,
                                                  zip(responses, [output_path] * len(responses)))
            metadata_pool.close()
            metadata_pool.join()

            if self.verbose:
                Printer.success(f'Metadata gathered for {len(metadata_list)} files.')

            completion_status = dict(map(lambda r: (r, False), responses))
            size_dict = dict(map(lambda m: (m["uuid"], [0, m["filesize"]]), metadata_list))
            total_size = sum(map(lambda m: m["filesize"], metadata_list))
            count_data: [int, int] = [0, len(metadata_list)]
            progress = Progress(0, total_size, 0, 10)

            success_table_data = map(lambda m: [m["filename"], FileUtils.get_readable_file_size(m["filesize"])],
                                     metadata_list)
            failure_table_data = map(lambda r: [r.url, "Failed"],
                                     failed_responses)
            table_data = list(success_table_data) + list(failure_table_data)
            table_printer = TablePrinter(table_data)
            table_printer.title_data = ["Filename", "Filesize/Status"]
            table_printer.align_list = [Alignment.LEFT, Alignment.RIGHT]
            table_printer.enumerated = True
            table_printer.border_style = BorderStyle.SINGLE
            table_printer.border_color = "#FFCC75"
            table_printer.enumeration_color = "#FFCC75"

            download_pool = ThreadPool(self.parallel_downloads)
            init_callback = lambda init_data: self._download_list_progress_init(progress)
            progress_callback = lambda progress_data: self._download_list_progress_callback(progress_data, progress,
                                                                                            size_dict, count_data,
                                                                                            completion_status)

            if self.verbose:
                Printer.info(
                    f'Starting download process for {len(metadata_list)} files ({FileUtils.get_readable_file_size(total_size)})')
            download_pool.starmap(self._download, zip(responses, metadata_list, [output_path] * len(responses),
                                                      [init_callback] * len(responses),
                                                      [progress_callback] * len(responses)))
            download_pool.close()
            download_pool.join()

            if self.verbose:
                Printer.success(
                    f'{os.linesep}Downloaded {len(metadata_list)} files ({FileUtils.get_readable_file_size(total_size)})')

            table_printer.print()

    @staticmethod
    def _download_list_progress_init(progress: Progress):
        progress.start()
        pass

    @staticmethod
    def _download_list_progress_callback(data: ProgressData, progress: Progress,
                                         size_dict: dict[str, list[int, int]],
                                         count_data: [int, int],
                                         completion_status: dict[str, bool]):
        size_dict[data["uuid"]][0] = data["downloaded"]

        downloaded = sum([s[0] for s in size_dict.values()])
        total_size = sum([s[1] for s in size_dict.values()])
        total_size_str = FileUtils.get_readable_file_size(total_size)
        info = f'[{FileUtils.get_readable_file_size(downloaded)}/{total_size_str}] ({count_data[0]}/{count_data[1]})'
        progress.update_value(downloaded)
        progress.set_info(info)
        if data["finished"]:
            completion_status[data["uuid"]] = True
            count_data[0] += 1
            if count_data[0] == count_data[1]:
                progress.update_value(total_size)
                info = f'[{FileUtils.get_readable_file_size(downloaded)}/{total_size_str}] ({count_data[0]}/{count_data[1]})'
                progress.set_info(info)
                time.sleep(1)
                progress.stop()

    def _get_download_metadata(self, response: requests.Response, output_path: str) -> DownloadMetadata:
        filename = self._get_filename(response)
        filepath = os.path.join(output_path, filename)
        filesize = int(response.headers["Content-Length"] if "Content-Length" in response.headers.keys() else 1)
        return {
            "filename": filename,
            "filepath": filepath,
            "filesize": filesize,
            "url": response.url,
            "uuid": str(uuid.uuid4()),
        }

    def _get_responses(self, urls: list[str]) -> list[requests.Response]:
        pool = ThreadPool(self.parallel_downloads)
        response_list = pool.map(self._get_response, urls)
        responses = [r for r in response_list if r is not None]
        pool.close()
        pool.join()
        return responses

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
