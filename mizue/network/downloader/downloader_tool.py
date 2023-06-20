import concurrent.futures
import json
import os
import time
from dataclasses import dataclass

from mizue.file import FileUtils
from mizue.network.downloader import DownloadStartEvent, ProgressEventArgs, DownloadCompleteEvent, Downloader, \
    DownloadEventType, DownloadFailureEvent
from mizue.printer import Printer
from mizue.printer.grid import ColumnSettings, Alignment, Grid, BorderStyle, CellRendererArgs
from mizue.progress import LabelRendererArgs, \
    InfoSeparatorRendererArgs, InfoTextRendererArgs, ColorfulProgress
from mizue.util import EventListener


@dataclass
class _DownloadReport:
    filename: str
    filesize: int
    url: str


class DownloaderTool(EventListener):
    def __init__(self):
        super().__init__()
        self._file_color_scheme = {}
        self._report_data: list[_DownloadReport] = []
        self._bulk_download_size = 0
        self._downloaded_count = 0
        self._total_download_count = 0
        self._success_count = 0  # For bulk downloads
        self._failure_count = 0  # For bulk downloads

        self.display_report = True
        """Whether to display the download report after the download is complete"""

        self.progress: ColorfulProgress | None = None
        self._load_color_scheme()

    def download(self, url: str, output_path: str):
        """
        Download a file to a specified directory
        :param url: The URL to download
        :param output_path: The output directory
        :return: None
        """
        filepath = []
        downloader = Downloader()
        downloader.add_event(DownloadEventType.STARTED, lambda event: self._on_download_start(event, filepath))
        downloader.add_event(DownloadEventType.PROGRESS, lambda event: self._on_download_progress(event))
        downloader.add_event(DownloadEventType.COMPLETED, lambda event: self._on_download_complete(event))
        downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_download_failure(event))
        try:
            downloader.download(url, output_path)
        except KeyboardInterrupt:
            downloader.close()
            self.progress.stop()
            Printer.warning(f"{os.linesep}Keyboard interrupt detected. Cleaning up...")
            if len(filepath) > 0:
                os.remove(filepath[0])
            self._report_data.append(_DownloadReport(url, 0, url))

        if self.display_report:
            self._print_report()

    def download_bulk(self, urls: list[str] | list[tuple[str, str]], output_path: str | None = None, parallel: int = 4):
        """
        Download a list of files to a specified directory or a list of [url, output_path] tuples.

        If the urls parameter is a list of [url, output_path] tuples, every url will be downloaded to its corresponding
        output_path.

        If the urls parameter is a list of urls, every url will be downloaded to the output_path parameter.
        In this case, the output_path parameter must be specified.
        :param urls: A list of urls or a list of [url, output_path] tuples
        :param output_path: The output directory if the urls parameter is a list of urls
        :param parallel: Number of parallel downloads
        :return: None
        """
        if isinstance(urls[0], tuple):
            self.download_tuple(urls, parallel)
        else:
            self.download_list(urls, output_path, parallel)

    def download_list(self, urls: list[str], output_path: str, parallel: int = 4):
        """
        Download a list of files to a specified directory
        :param urls: The list of URLs to download
        :param output_path: The output directory
        :param parallel: Number of parallel downloads
        :return: None
        """
        self.download_tuple([(url, output_path) for url in urls], parallel)

    def download_tuple(self, urls: list[tuple[str, str]], parallel: int = 4):
        """
        Download a list of [url, output_path] tuples. Every url will be downloaded to its corresponding output_path.
        :param urls: A list of [url, output_path] tuples
        :param parallel: Number of parallel downloads
        :return: None
        """

        self.progress = ColorfulProgress(start=0, end=len(urls), value=0)
        self._configure_progress()
        self.progress.start()
        self._downloaded_count = 0
        self._total_download_count = len(urls)
        self._report_data = []
        self._success_count = 0
        self._failure_count = 0
        download_dict = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            try:
                responses: list[concurrent.futures.Future] = []
                downloader = Downloader()
                downloader.add_event(DownloadEventType.PROGRESS,
                                     lambda event: self._on_bulk_download_progress(event, download_dict))
                downloader.add_event(DownloadEventType.COMPLETED,
                                     lambda event: self._on_bulk_download_complete(event))
                downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_bulk_download_failed(event))
                for url, output_path in list(set(urls)):
                    responses.append(executor.submit(downloader.download, url, output_path))
                for response in concurrent.futures.as_completed(responses):
                    self._downloaded_count += 1
                    self.progress.update_value(self._downloaded_count)
                    self.progress.info_text = self._get_bulk_progress_info(download_dict)
                executor.shutdown(wait=True)
            except KeyboardInterrupt:
                downloader.close()
                self.progress.stop()
                Printer.warning(f"{os.linesep}Keyboard interrupt detected. Cleaning up...")
                executor.shutdown(wait=False, cancel_futures=True)
        self.progress.stop()
        if self.display_report:
            self._print_report()

    def _configure_progress(self):
        self.progress.info_separator_renderer = self._info_separator_renderer
        self.progress.info_text_renderer = self._info_text_renderer
        self.progress.label_renderer = self._label_renderer
        self.progress.label = "Downloading: "

    @staticmethod
    def _get_basic_colored_text(text: str, percentage: float):
        return ColorfulProgress.get_basic_colored_text(text, percentage)

    def _get_bulk_progress_info(self, download_dict: dict):
        file_progress_text = f'⟪{self._downloaded_count}/{self._total_download_count}⟫'
        size_text = FileUtils.get_readable_file_size(sum(download_dict.values()))
        return f'{file_progress_text} ⟪{size_text}⟫'

    @staticmethod
    def _info_separator_renderer(args: InfoSeparatorRendererArgs):
        return ColorfulProgress.get_basic_colored_text(" | ", args.percentage)

    def _info_text_renderer(self, args: InfoTextRendererArgs):
        info_text = DownloaderTool._get_basic_colored_text(args.text, args.percentage)
        separator = ColorfulProgress.get_basic_colored_text(" | ", args.percentage)
        successful_text = Printer.format_hex(f'{self._success_count}', '#0EB33B')
        failed_text = Printer.format_hex(f'{self._failure_count}', '#FF0000')
        status_text = str.format("{}{}{}{}{}",
                                 ColorfulProgress.get_basic_colored_text("⟪", args.percentage),
                                 successful_text,
                                 ColorfulProgress.get_basic_colored_text("/", args.percentage),
                                 failed_text,
                                 ColorfulProgress.get_basic_colored_text("⟫", args.percentage))
        full_info_text = str.format("{}{}{}", info_text, separator, status_text)
        return full_info_text

    @staticmethod
    def _label_renderer(args: LabelRendererArgs):
        if args.percentage < 100:
            return Printer.format_hex(args.label, '#FFCC75')
        return Printer.format_hex('Downloaded: ', '#0EB33B')

    def _load_color_scheme(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "colors.json")
        with open(file_path, "r") as f:
            self._file_color_scheme = json.load(f)

    def _on_bulk_download_complete(self, event: DownloadCompleteEvent):
        self._report_data.append(_DownloadReport(event.filename, event.filesize, event.url))
        self._success_count += 1

    def _on_bulk_download_failed(self, event: DownloadFailureEvent):
        self._report_data.append(_DownloadReport("", 0, event.url))
        self._failure_count += 1

    def _on_bulk_download_progress(self, event: ProgressEventArgs, download_dict: dict):
        download_dict[event.url] = event.downloaded
        self.progress.info_text = self._get_bulk_progress_info(download_dict)

    def _on_download_complete(self, event: DownloadCompleteEvent):
        self.progress.update_value(event.filesize)
        downloaded_info = FileUtils.get_readable_file_size(event.filesize)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.info_text = info
        time.sleep(0.5)
        self.progress.stop()
        self._report_data.append(_DownloadReport(event.filename, event.filesize, event.url))
        self._fire_event(DownloadEventType.COMPLETED, event)

    def _on_download_failure(self, event: DownloadFailureEvent):
        if isinstance(event.exception, KeyboardInterrupt):
            Printer.warning("Download has been cancelled by user.")
            print(os.linesep)
        if self.progress:
            self.progress.terminate()
        self._report_data.append(_DownloadReport("", 0, event.url))
        self._fire_event(DownloadEventType.FAILED, event)

    def _on_download_progress(self, event: ProgressEventArgs):
        self.progress.update_value(event.downloaded)
        downloaded_info = FileUtils.get_readable_file_size(event.downloaded)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.info_text = info
        self._fire_event(DownloadEventType.PROGRESS, event)

    def _on_download_start(self, event: DownloadStartEvent, filepath: list[str]):
        self.progress = ColorfulProgress(start=0, end=event.filesize, value=0)
        self._configure_progress()
        self.progress.start()
        filepath.append(event.filepath)
        self._fire_event(DownloadEventType.STARTED, event)

    def _print_report(self):
        success_data = [report for report in self._report_data if report.filesize > 0]
        failed_data = [report for report in self._report_data if report.filesize == 0]
        row_index = 1
        success_grid_data = []
        for report in success_data:
            filename, ext = os.path.splitext(report.filename)
            success_grid_data.append(
                [row_index, report.filename, ext[1:], FileUtils.get_readable_file_size(report.filesize)])
            row_index += 1

        failed_grid_data = []
        for report in failed_data:
            failed_grid_data.append([row_index, report.url, "", 'Failed'])
            row_index += 1

        grid_columns: list[ColumnSettings] = [
            ColumnSettings(title='#', alignment=Alignment.RIGHT,
                           renderer=lambda x: Printer.format_hex(x.cell, '#FFCC75')),
            ColumnSettings(title='Filename/URL', renderer=self._report_grid_file_column_cell_renderer),
            ColumnSettings(title='Type', alignment=Alignment.RIGHT,
                           renderer=self._report_grid_file_type_column_cell_renderer),
            ColumnSettings(title='Filesize/Status', alignment=Alignment.RIGHT,
                           renderer=lambda x: Printer.format_hex(x.cell, '#FF0000')
                           if x.cell == 'Failed' else self._report_grid_cell_renderer(x))
        ]
        grid = Grid(grid_columns, success_grid_data + failed_grid_data)
        grid.border_style = BorderStyle.SINGLE
        grid.border_color = '#FFCC75'
        grid.cell_renderer = self._report_grid_cell_renderer
        print(os.linesep)
        grid.print()

    @staticmethod
    def _report_grid_cell_renderer(args: CellRendererArgs):
        if args.cell.endswith("KB"):
            return Printer.format_hex(args.cell, '#00a9ff')
        if args.cell.endswith("MB"):
            return Printer.format_hex(args.cell, '#d2309a')
        if args.is_header:
            return Printer.format_hex(args.cell, '#FFCC75')
        return args.cell

    def _report_grid_file_column_cell_renderer(self, args: CellRendererArgs):
        if args.is_header:
            return Printer.format_hex(args.cell, '#FFCC75')
        file, ext = os.path.splitext(args.cell)
        color = self._file_color_scheme.get(ext[1:], '#FFFFFF')
        return Printer.format_hex(args.cell, color)

    def _report_grid_file_type_column_cell_renderer(self, args: CellRendererArgs):
        if args.is_header:
            return Printer.format_hex(args.cell, '#FFCC75')
        color = self._file_color_scheme.get(args.cell, '#FFFFFF')
        return Printer.format_hex(args.cell, color)
