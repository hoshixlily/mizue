import concurrent.futures
import multiprocessing
import os
import time

from mizue.file import FileUtils
from mizue.network.downloader import DownloadStartEvent, ProgressEventArgs, DownloadCompleteEvent, Downloader, \
    DownloadEventType, DownloadFailureEvent
from mizue.printer import Printer
from mizue.progress import Progress


class DownloaderTool:
    def __init__(self):
        self._bulk_download_size = 0
        self._downloaded_count = 0
        self._total_download_count = 0
        self.progress: Progress | None = None

    def download(self, url: str, output_path: str):
        downloader = Downloader()
        downloader.add_event(DownloadEventType.STARTED, lambda event: self._on_download_start(event))
        downloader.add_event(DownloadEventType.PROGRESS, lambda event: self._on_download_progress(event))
        downloader.add_event(DownloadEventType.COMPLETED, lambda event: self._on_download_complete(event))
        downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_download_failure(event))
        downloader.download(url, output_path)

    def download_bulk(self, urls: list[str], output_path: str, parallel: int = 4):
        self.progress = Progress(start=0, end=len(urls), value=0)
        self.progress.set_label("Downloading: ")
        self.progress.start()
        self._downloaded_count = 0
        self._total_download_count = len(urls)
        download_dict = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            try:
                responses: list[concurrent.futures.Future] = []
                downloader = Downloader()
                downloader.add_event(DownloadEventType.PROGRESS,
                                     lambda event: self._on_bulk_download_progress(event, download_dict))
                downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_bulk_download_failed(event))
                for url in list(set(urls)):
                    responses.append(executor.submit(downloader.download, url, output_path))
                for response in concurrent.futures.as_completed(responses):
                    self._downloaded_count += 1
                    self.progress.update_value(self._downloaded_count)
                    self.progress.set_info(self._get_bulk_progress_info(download_dict))
                executor.shutdown(wait=True)
            except KeyboardInterrupt:
                downloader.close()
                self.progress.stop()
                Printer.info(f"{os.linesep}Keyboard interrupt detected. Waiting for ongoing downloads to finish...")
                executor.shutdown(wait=False, cancel_futures=True)
        self.progress.stop()

    def _get_bulk_progress_info(self, download_dict: dict):
        file_progress_text = f'[{self._downloaded_count}/{self._total_download_count}]'
        size_text = FileUtils.get_readable_file_size(sum(download_dict.values()))
        return f'{file_progress_text} [{size_text}]'

    def _on_bulk_download_failed(self, event: DownloadFailureEvent):
        pass
        # print(f"Failed to download {event.url}")

    def _on_bulk_download_progress(self, event: ProgressEventArgs, download_dict: dict):
        download_dict[event.url] = event.downloaded
        self.progress.set_info(self._get_bulk_progress_info(download_dict))

    def _on_download_complete(self, event: DownloadCompleteEvent):
        self.progress.update_value(event.filesize)
        downloaded_info = FileUtils.get_readable_file_size(event.filesize)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.set_info(info)
        time.sleep(0.5)
        self.progress.stop()

    def _on_download_failure(self, event: DownloadFailureEvent):
        if isinstance(event.exception, KeyboardInterrupt):
            Printer.warning("Download has been cancelled by user.")
            print(os.linesep)
        self.progress.terminate()

    def _on_download_progress(self, event: ProgressEventArgs):
        self.progress.update_value(event.downloaded)
        downloaded_info = FileUtils.get_readable_file_size(event.downloaded)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.set_info(info)

    def _on_download_start(self, event: DownloadStartEvent):
        self.progress = Progress(start=0, end=event.filesize, value=0)
        self.progress.set_label("Downloading: ")
        self.progress.start()
