import concurrent.futures
import json
import os
import time
from dataclasses import dataclass
from enum import Enum

from mizue.file import FileUtils
from mizue.network.downloader import DownloadStartEvent, ProgressEventArgs, DownloadCompleteEvent, Downloader, \
    DownloadEventType, DownloadFailureEvent
from mizue.network.downloader.download_event import DownloadSkipEvent
from mizue.printer import Printer, Colorizer
from mizue.printer.grid import ColumnSettings, Alignment, Grid, BorderStyle, CellRendererArgs
from mizue.progress import LabelRendererArgs, \
    InfoSeparatorRendererArgs, InfoTextRendererArgs, ColorfulProgress
from mizue.util import EventListener


class ReportReason(Enum):
    COMPLETED = 1,
    FAILED = 2,
    SKIPPED = 3


@dataclass
class _DownloadReport:
    filename: str
    filesize: int
    reason: ReportReason
    url: str


@dataclass
class _DownloadReportGridData:
    ext: str
    filename: str
    filesize: str
    row_index: int
    status: DownloadEventType


class DownloaderTool(EventListener):
    def __init__(self):
        super().__init__()
        self._file_color_scheme = {}
        self._report_data: list[_DownloadReport] = []
        self._bulk_download_size = 0
        self._downloaded_count = 0
        self._total_download_count = 0
        self._failure_count = 0  # For bulk downloads
        self._success_count = 0  # For bulk downloads
        self._skip_count = 0     # For bulk downloads

        self.display_report = True
        """Whether to display the download report after the download is complete"""

        self.force_download = False
        """Whether to force the download even if the file already exists"""

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
        downloader.force_download = self.force_download
        downloader.add_event(DownloadEventType.STARTED, lambda event: self._on_download_start(event, filepath))
        downloader.add_event(DownloadEventType.PROGRESS, lambda event: self._on_download_progress(event))
        downloader.add_event(DownloadEventType.COMPLETED, lambda event: self._on_download_complete(event))
        downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_download_failure(event))
        downloader.add_event(DownloadEventType.SKIPPED, lambda event: self._on_download_skip(event))
        try:
            downloader.download(url, output_path)
        except KeyboardInterrupt:
            downloader.close()
            self.progress.stop()
            Printer.warning(f"{os.linesep}Keyboard interrupt detected. Cleaning up...")
            if len(filepath) > 0:
                os.remove(filepath[0])
            self._report_data.append(_DownloadReport(url, 0, ReportReason.FAILED, url))

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
                downloader.force_download = self.force_download
                downloader.add_event(DownloadEventType.PROGRESS,
                                     lambda event: self._on_bulk_download_progress(event, download_dict))
                downloader.add_event(DownloadEventType.COMPLETED,
                                     lambda event: self._on_bulk_download_complete(event))
                downloader.add_event(DownloadEventType.FAILED, lambda event: self._on_bulk_download_failed(event))
                downloader.add_event(DownloadEventType.SKIPPED, lambda event: self._on_bulk_download_skip(event))
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
        self.progress.label = Colorizer.colorize("Downloading: ", bold=True)

    @staticmethod
    def _get_basic_colored_text(text: str, percentage: float):
        return ColorfulProgress.get_basic_colored_text(text, percentage)

    def _get_bulk_progress_info(self, download_dict: dict):
        downloaded_str = f"{self._downloaded_count}".zfill(len(str(self._total_download_count)))
        file_progress_text = f'⟪◆⎯ {downloaded_str}/{self._total_download_count} ⎯◆⟫'
        size_text = FileUtils.get_readable_file_size(sum(download_dict.values()))
        return f'{file_progress_text} ⟪◆⎯ {size_text} ⎯◆⟫'

    @staticmethod
    def _get_download_event_type_text(event_type: DownloadEventType):
        if event_type == DownloadEventType.COMPLETED:
            return "Completed"
        if event_type == DownloadEventType.FAILED:
            return "Failed"
        if event_type == DownloadEventType.PROGRESS:
            return "Progress"
        if event_type == DownloadEventType.SKIPPED:
            return "Skipped"
        if event_type == DownloadEventType.STARTED:
            return "Started"
        return "Unknown"

    @staticmethod
    def _info_separator_renderer(args: InfoSeparatorRendererArgs):
        return ColorfulProgress.get_basic_colored_text(" | ", args.percentage)

    def _info_text_renderer(self, args: InfoTextRendererArgs):
        info_text = DownloaderTool._get_basic_colored_text(args.text, args.percentage)
        separator = ColorfulProgress.get_basic_colored_text(" | ", args.percentage)
        successful_text = Colorizer.colorize(f'{self._success_count}', '#9acd32')
        failed_text = Colorizer.colorize(f'{self._failure_count}', '#FF0000')
        skipped_text = Colorizer.colorize(f'{self._skip_count}', '#777777')
        status_text = str.format("{}{}{}{}{}{}{}",
                                 ColorfulProgress.get_basic_colored_text("⟪◆⎯ ", args.percentage),
                                 successful_text,
                                 ColorfulProgress.get_basic_colored_text(" ◆ ", args.percentage),
                                 failed_text,
                                 ColorfulProgress.get_basic_colored_text(" ◆ ", args.percentage),
                                 skipped_text,
                                 ColorfulProgress.get_basic_colored_text(" ⎯◆⟫", args.percentage))
        full_info_text = str.format("{}{}{}", info_text, separator, status_text)
        return full_info_text

    @staticmethod
    def _label_renderer(args: LabelRendererArgs):
        if args.percentage < 100:
            return Colorizer.colorize(args.label, '#FFCC75')
        return Colorizer.colorize('Downloaded: ', '#0EB33B')

    def _load_color_scheme(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "colors.json")
        with open(file_path, "r") as f:
            self._file_color_scheme = json.load(f)

    def _on_bulk_download_complete(self, event: DownloadCompleteEvent):
        self._report_data.append(_DownloadReport(event.filename, event.filesize, ReportReason.COMPLETED, event.url))
        self._success_count += 1

    def _on_bulk_download_failed(self, event: DownloadFailureEvent):
        self._report_data.append(_DownloadReport("", 0, ReportReason.FAILED, event.url))
        self._failure_count += 1

    def _on_bulk_download_progress(self, event: ProgressEventArgs, download_dict: dict):
        download_dict[event.url] = event.downloaded
        self.progress.info_text = self._get_bulk_progress_info(download_dict)

    def _on_bulk_download_skip(self, event: DownloadSkipEvent):
        self._report_data.append(_DownloadReport(event.filename, 0, ReportReason.SKIPPED, event.url))
        self._skip_count += 1

    def _on_download_complete(self, event: DownloadCompleteEvent):
        self.progress.update_value(event.filesize)
        downloaded_info = FileUtils.get_readable_file_size(event.filesize)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.info_text = info
        time.sleep(0.5)
        self.progress.stop()
        self._report_data.append(_DownloadReport(event.filename, event.filesize, ReportReason.COMPLETED, event.url))
        self._fire_event(DownloadEventType.COMPLETED, event)

    def _on_download_failure(self, event: DownloadFailureEvent):
        if isinstance(event.exception, KeyboardInterrupt):
            Printer.warning("Download has been cancelled by user.")
            print(os.linesep)
        if self.progress:
            self.progress.terminate()
        self._report_data.append(_DownloadReport("", 0, ReportReason.FAILED, event.url))
        self._fire_event(DownloadEventType.FAILED, event)

    def _on_download_progress(self, event: ProgressEventArgs):
        self.progress.update_value(event.downloaded)
        downloaded_info = FileUtils.get_readable_file_size(event.downloaded)
        filesize_info = FileUtils.get_readable_file_size(event.filesize)
        info = f'[{downloaded_info}/{filesize_info}]'
        self.progress.info_text = info
        self._fire_event(DownloadEventType.PROGRESS, event)

    def _on_download_skip(self, event: DownloadSkipEvent):
        self._report_data.append(_DownloadReport(event.filename, 0, ReportReason.SKIPPED, event.url))
        self._fire_event(DownloadEventType.SKIPPED, event)

    def _on_download_start(self, event: DownloadStartEvent, filepath: list[str]):
        self.progress = ColorfulProgress(start=0, end=event.filesize, value=0)
        self._configure_progress()
        self.progress.start()
        filepath.append(event.filepath)
        self._fire_event(DownloadEventType.STARTED, event)

    def _print_report(self):
        success_data = [report for report in self._report_data if report.reason == ReportReason.COMPLETED]
        failed_data = [report for report in self._report_data if report.reason == ReportReason.FAILED]
        skipped_data = [report for report in self._report_data if report.reason == ReportReason.SKIPPED]
        row_index = 1
        success_grid_data: list[_DownloadReportGridData] = []
        for report in success_data:
            filename, ext = os.path.splitext(report.filename)
            success_grid_data.append(
                _DownloadReportGridData(ext[1:], report.filename,
                                        FileUtils.get_readable_file_size(report.filesize), row_index,
                                        DownloadEventType.COMPLETED)
            )
            row_index += 1

        failed_grid_data = []
        for report in failed_data:
            url, ext = os.path.splitext(report.url)
            failed_grid_data.append(
                _DownloadReportGridData(ext[1:], report.url,
                                        FileUtils.get_readable_file_size(report.filesize), row_index,
                                        DownloadEventType.FAILED)
            )
            row_index += 1

        skipped_grid_data = []
        for report in skipped_data:
            url, ext = os.path.splitext(report.url)
            skipped_grid_data.append(
                _DownloadReportGridData(ext[1:], report.url,
                                        FileUtils.get_readable_file_size(report.filesize), row_index,
                                        DownloadEventType.SKIPPED)
            )
            row_index += 1

        grid_columns: list[ColumnSettings] = [
            ColumnSettings(title='#', alignment=Alignment.RIGHT, wrap=False,
                           renderer=lambda x: Colorizer.colorize(x.cell, '#FFCC75')),
            ColumnSettings(title='Filename/URL', wrap=False, renderer=self._report_grid_file_column_cell_renderer),
            ColumnSettings(title='Type', alignment=Alignment.RIGHT,
                           renderer=self._report_grid_file_type_column_cell_renderer),
            ColumnSettings(title='Filesize', alignment=Alignment.RIGHT,
                           renderer=self._report_grid_cell_renderer),
            ColumnSettings(title='Status', alignment=Alignment.RIGHT,
                           renderer=self._report_grid_cell_renderer)
        ]

        grid_data: list[list[str]] = []
        for data_item in success_grid_data + failed_grid_data + skipped_grid_data:
            grid_data.append([
                str(data_item.row_index),
                data_item.filename,
                data_item.ext,
                data_item.filesize,
                self._get_download_event_type_text(data_item.status)
            ])

        grid = Grid(grid_columns, grid_data)
        grid.border_style = BorderStyle.SINGLE
        grid.border_color = '#FFCC75'
        grid.cell_renderer = self._report_grid_cell_renderer
        print(os.linesep)
        # grid.fill_screen()
        grid.print()

    @staticmethod
    def _report_grid_cell_renderer(args: CellRendererArgs):
        if args.cell == 'Failed':
            return Colorizer.colorize(args.cell, '#FF0000')
        if args.cell == 'Skipped':
            return Colorizer.colorize(args.cell, '#777777')
        if args.cell == 'Completed':
            return Colorizer.colorize(args.cell, '#0EB33B')
        if args.cell.endswith("KB"):
            return Colorizer.colorize(args.cell, '#00a9ff')
        if args.cell.endswith("MB"):
            return Colorizer.colorize(args.cell, '#d2309a')
        if args.is_header:
            return Colorizer.colorize(args.cell, '#FFCC75')
        return args.cell

    def _report_grid_file_column_cell_renderer(self, args: CellRendererArgs):
        if args.is_header:
            return Colorizer.colorize(args.cell, '#FFCC75')
        file, ext = os.path.splitext(args.cell)
        color = self._file_color_scheme.get(ext[1:], '#FFFFFF')
        return Colorizer.colorize(args.cell, color)

    def _report_grid_file_type_column_cell_renderer(self, args: CellRendererArgs):
        if args.is_header:
            return Colorizer.colorize(args.cell, '#FFCC75')
        color = self._file_color_scheme.get(args.cell, '#FFFFFF')
        return Colorizer.colorize(args.cell, color)
