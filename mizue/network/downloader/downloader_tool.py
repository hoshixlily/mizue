import concurrent.futures
import json
import os
import threading # Import threading for Lock
import urllib.parse # Added missing import here
from collections import defaultdict # Use defaultdict for progress tracking
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Union # Added Optional, Union

from mizue.file import FileUtils
from mizue.network.downloader import (DownloadStartEvent, ProgressEventArgs,
                                      DownloadCompleteEvent, Downloader,
                                      DownloadEventType, DownloadFailureEvent)
from mizue.network.downloader.download_event import DownloadSkipEvent
from mizue.printer import Printer, Colorizer
from mizue.printer.grid import (ColumnSettings, Alignment, Grid, BorderStyle,
                                CellRendererArgs)
from mizue.progress import (LabelRendererArgs, InfoSeparatorRendererArgs,
                            InfoTextRendererArgs, ColorfulProgress)
from mizue.util import EventListener


class ReportReason(Enum):
    COMPLETED = 1
    FAILED = 2
    SKIPPED = 3


@dataclass
class _DownloadReport:
    filename: str # Can be URL for failed/skipped
    filesize: int
    reason: ReportReason
    url: str


@dataclass
class _DownloadReportGridData:
    ext: str
    filename_or_url: str # Clarified name
    filesize_str: str # Clarified name
    row_index: int
    status: ReportReason # Use ReportReason for status mapping


class DownloaderTool(EventListener):
    """Orchestrates single/bulk file downloads with progress and reports."""

    def __init__(self):
        super().__init__()
        self._file_color_scheme: Dict = {}
        self._report_data: List[_DownloadReport] = []
        self._bulk_progress_lock = threading.Lock() # Lock for shared bulk download state
        self._bulk_active_progress: Dict[str, int] = defaultdict(int) # Tracks current size per URL {url: downloaded_bytes}
        self._bulk_total_downloaded_size: int = 0 # Separate counter for total size for efficiency
        self._downloaded_count: int = 0
        self._total_download_count: int = 0
        self._failure_count: int = 0
        self._success_count: int = 0
        self._skip_count: int = 0

        self.display_report: bool = True
        """Whether to display the download report after the download is complete"""

        self.force_download: bool = False
        """Whether to force the download even if the file already exists"""

        self.progress: Optional[ColorfulProgress] = None
        """The active progress bar instance"""

        self._load_color_scheme()

    # --- Public Download Methods ---

    def download(self, url: str, output_path: str):
        """
        Download a single file to a specified directory with progress.

        Args:
            url: The URL to download.
            output_path: The output directory.
        """
        self._reset_single_download_state()
        filepath_ref = [] # Use list as mutable reference to pass into lambda

        downloader = Downloader()
        downloader.force_download = self.force_download
        # Add event listeners specific to this single download
        # Using lambdas captures the current state (downloader, filepath_ref)
        start_id = downloader.add_event(DownloadEventType.STARTED,
                                  lambda event: self._on_download_start(event, filepath_ref))
        prog_id = downloader.add_event(DownloadEventType.PROGRESS,
                                 lambda event: self._on_download_progress(event))
        comp_id = downloader.add_event(DownloadEventType.COMPLETED,
                                 lambda event: self._on_download_complete(event))
        fail_id = downloader.add_event(DownloadEventType.FAILED,
                                 lambda event: self._on_download_failure(event))
        skip_id = downloader.add_event(DownloadEventType.SKIPPED,
                                 lambda event: self._on_download_skip(event))

        try:
            downloader.download(url, output_path)
        except KeyboardInterrupt:
            if self.progress:
                self.progress.terminate() # Use terminate for abrupt stop
            downloader.close() # Signal downloader to stop
            Printer.warning(f"{os.linesep}Keyboard interrupt detected. Cleaning up...")
            # Attempt cleanup only if filepath was captured
            if filepath_ref and os.path.exists(filepath_ref[0]):
                try:
                    os.remove(filepath_ref[0])
                    Printer.info(f"Removed partial file: {filepath_ref[0]}")
                except OSError as e:
                    Printer.error(f"Could not remove partial file {filepath_ref[0]}: {e}")
            # Manually add failure report for interrupted download
            self._report_data.append(_DownloadReport("", 0, ReportReason.FAILED, url))
        finally:
            # Ensure progress bar stops if it was started
            if self.progress and self.progress._active:
                 self.progress.stop() # Graceful stop if not terminated
            self.progress = None # Clear progress bar instance

            # Clean up listeners for this specific downloader instance
            downloader.remove_event(start_id)
            downloader.remove_event(prog_id)
            downloader.remove_event(comp_id)
            downloader.remove_event(fail_id)
            downloader.remove_event(skip_id)

        if self.display_report and self._report_data:
            self._print_report()

    def download_bulk(self, urls: Union[List[str], List[Tuple[str, str]]],
                      output_path: Optional[str] = None, parallel: int = 4):
        """
        Download a list of files concurrently.

        Args:
            urls: A list of URLs, or a list of (url, output_path) tuples.
            output_path: The common output directory if urls is a list of strings.
                         Required in that case. Ignored if urls is list of tuples.
            parallel: Number of parallel download workers.
        """
        if not urls:
            Printer.warning("No URLs provided for bulk download.")
            return

        if isinstance(urls[0], tuple):
            # Input is List[Tuple[str, str]]
            download_tasks = list(set(urls)) # Remove duplicate url/path pairs
            self._execute_bulk_download(download_tasks, parallel)
        elif isinstance(urls[0], str):
            # Input is List[str]
            if output_path is None:
                raise ValueError("output_path must be specified when providing a list of URLs.")
            # Convert List[str] to List[Tuple[str, str]]
            download_tasks = list(set([(url, output_path) for url in urls])) # Remove duplicate urls
            self._execute_bulk_download(download_tasks, parallel)
        else:
            raise TypeError("Unsupported format for 'urls'. Expected List[str] or List[Tuple[str, str]].")

    # --- Private Helper Methods ---

    def _execute_bulk_download(self, tasks: List[Tuple[str, str]], parallel: int):
        """Internal method to perform the actual bulk download."""
        self._reset_bulk_download_state(len(tasks))
        self.progress = ColorfulProgress(start=0, end=self._total_download_count, value=0)
        self._configure_progress()
        self.progress.start()

        downloader = Downloader() # Single downloader instance for all threads
        downloader.force_download = self.force_download
        # Add event listeners ONCE for the shared downloader
        start_id = downloader.add_event(DownloadEventType.STARTED, self._on_bulk_download_start)
        prog_id = downloader.add_event(DownloadEventType.PROGRESS, self._on_bulk_download_progress)
        comp_id = downloader.add_event(DownloadEventType.COMPLETED, self._on_bulk_download_complete)
        fail_id = downloader.add_event(DownloadEventType.FAILED, self._on_bulk_download_failed)
        skip_id = downloader.add_event(DownloadEventType.SKIPPED, self._on_bulk_download_skip)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = [executor.submit(downloader.download, url, path) for url, path in tasks]
                try:
                    # Process futures as they complete
                    for future in concurrent.futures.as_completed(futures):
                        # Result retrieval can re-raise exceptions from the download task
                        try:
                             future.result() # Check for exceptions raised within the download task itself
                        except Exception as exc:
                             # This exception likely already triggered a FAILED event via the downloader,
                             # but log it here for visibility if it wasn't caught/reported by downloader.
                             # Avoid double-counting failure if FAILED event was already processed.
                             # TODO: Need a way to correlate future exception with failure event if needed.
                             Printer.error(f"Error during download future execution: {exc}")
                             # Consider incrementing failure count here ONLY if not already counted by event? Risky.

                        # Update overall progress after each task finishes (success, fail, or skip)
                        # Use lock for counter updates
                        with self._bulk_progress_lock:
                            self._downloaded_count += 1
                            current_info_text = self._get_bulk_progress_info() # Get latest info
                        if self.progress: # Ensure progress exists
                            self.progress.update_value(self._downloaded_count)
                            self.progress.info_text = current_info_text

                except KeyboardInterrupt:
                    Printer.warning(f"{os.linesep}Keyboard interrupt detected during bulk download. Cancelling...")
                    # Cancel pending futures - Downloader's _alive flag should handle running ones
                    for f in futures:
                        f.cancel()
                    downloader.close() # Signal running downloads to stop
                    executor.shutdown(wait=False, cancel_futures=True) # Force shutdown
                    if self.progress:
                        self.progress.terminate() # Abrupt stop for progress bar
                    # Note: Report will show progress up to interruption

        finally:
            # Ensure progress stops gracefully if not already terminated
            if self.progress and self.progress._active:
                self.progress.update_value(self._downloaded_count) # Final update
                self.progress.stop()
            self.progress = None # Clear progress instance

            # Clean up shared downloader listeners
            downloader.remove_event(start_id)
            downloader.remove_event(prog_id)
            downloader.remove_event(comp_id)
            downloader.remove_event(fail_id)
            downloader.remove_event(skip_id)

            if self.display_report and self._report_data:
                self._print_report()


    def _reset_single_download_state(self):
        """Reset state specific to single downloads."""
        self._report_data = [] # Clear previous report
        # Reset single progress bar if necessary (or handle in download method)
        if self.progress:
            self.progress = None

    def _reset_bulk_download_state(self, total_tasks: int):
        """Reset state before starting a new bulk download."""
        self._report_data = []
        self._bulk_active_progress.clear()
        self._bulk_total_downloaded_size = 0
        self._downloaded_count = 0
        self._total_download_count = total_tasks
        self._failure_count = 0
        self._success_count = 0
        self._skip_count = 0
        if self.progress:
            self.progress = None

    def _load_color_scheme(self):
        """Loads file extension color mapping from JSON."""
        try:
            # Construct path relative to this file
            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(dir_path, "data", "colors.json")
            with open(file_path, "r", encoding='utf-8') as f: # Specify encoding
                self._file_color_scheme = json.load(f)
        except FileNotFoundError:
            Printer.warning(f"Color scheme file not found at {file_path}. Using defaults.")
            self._file_color_scheme = {}
        except json.JSONDecodeError:
            Printer.error(f"Error decoding color scheme file {file_path}.")
            self._file_color_scheme = {}
        except Exception as e:
            Printer.error(f"Failed to load color scheme: {e}")
            self._file_color_scheme = {}

    # --- Progress Bar Configuration ---

    def _configure_progress(self):
        """Sets up custom renderers for the ColorfulProgress bar."""
        if not self.progress: return
        self.progress.info_separator_renderer = self._info_separator_renderer
        self.progress.info_text_renderer = self._info_text_renderer
        self.progress.label_renderer = self._label_renderer
        # Determine label based on single/bulk context if needed, here assuming bulk
        # TODO: Maybe pass context to configure_progress?
        self.progress.label = Colorizer.colorize("Downloading: ", bold=True)


    # --- Event Handlers for Single Download ---

    def _on_download_start(self, event: DownloadStartEvent, filepath_ref: List[str]):
        """Callback for single download start."""
        # Create progress bar only when download actually starts
        if not self.progress:
             self.progress = ColorfulProgress(start=0, end=event.filesize if event.filesize > 0 else 1, value=0)
             self._configure_progress() # Configure before starting
             self.progress.start()
        else: # Reuse existing progress if somehow already created
             self.progress.set_end_value(event.filesize if event.filesize > 0 else 1)
             self.progress.update_value(0)


        filepath_ref.append(event.filepath) # Store the actual filepath
        self._fire_event(DownloadEventType.STARTED, event)

    def _on_download_progress(self, event: ProgressEventArgs):
        """Callback for single download progress."""
        if self.progress:
            # Handle case where filesize is 0 or unknown from header
            if event.filesize <= 0:
                 # Display indeterminate progress or just bytes downloaded
                 self.progress.set_end_value(1) # Prevent division by zero in bar render
                 self.progress.update_value(0) # Keep bar visually static or minimal
                 downloaded_info = FileUtils.get_readable_file_size(event.downloaded)
                 info = f'[{downloaded_info}/Unknown]'
            else:
                 self.progress.set_end_value(event.filesize) # Ensure end value is correct
                 self.progress.update_value(event.downloaded)
                 downloaded_info = FileUtils.get_readable_file_size(event.downloaded)
                 filesize_info = FileUtils.get_readable_file_size(event.filesize)
                 info = f'[{downloaded_info}/{filesize_info}]'

            self.progress.info_text = info
        self._fire_event(DownloadEventType.PROGRESS, event)

    def _on_download_complete(self, event: DownloadCompleteEvent):
        """Callback for single download completion."""
        if self.progress:
            final_filesize = event.filesize if event.filesize > 0 else 1 # Use 1 if unknown for bar
            self.progress.set_end_value(final_filesize)
            self.progress.update_value(final_filesize) # Ensure 100%
            downloaded_info = FileUtils.get_readable_file_size(event.filesize)
            self.progress.info_text = f'[{downloaded_info}/{downloaded_info}]'
            # Don't stop the progress bar here, let the finally block in download() handle it
            # time.sleep(0.5) # Avoid sleep in callback
            # self.progress.stop()
        self._report_data.append(_DownloadReport(event.filename, event.filesize, ReportReason.COMPLETED, event.url))
        self._fire_event(DownloadEventType.COMPLETED, event)

    def _on_download_failure(self, event: DownloadFailureEvent):
        """Callback for single download failure."""
        if self.progress:
             # Terminate progress bar immediately on failure
            self.progress.terminate()
        # Use URL if filename is not available (e.g., error before metadata)
        filename_or_url = event.filepath if event.filepath else event.url # Prefer filepath if known
        self._report_data.append(_DownloadReport(filename_or_url, 0, ReportReason.FAILED, event.url))
        self._fire_event(DownloadEventType.FAILED, event)

    def _on_download_skip(self, event: DownloadSkipEvent):
        """Callback for single download skip."""
        # Stop progress bar if it was somehow started for a skipped file
        if self.progress:
            self.progress.stop()
        self._report_data.append(_DownloadReport(event.filename, 0, ReportReason.SKIPPED, event.url))
        self._fire_event(DownloadEventType.SKIPPED, event)


    # --- Event Handlers for Bulk Download (Thread-Safe) ---

    def _on_bulk_download_start(self, event: DownloadStartEvent):
        """Callback for bulk download start (runs in worker thread)."""
        # This event isn't strictly needed for bulk progress bar, but forward it
        self._fire_event(DownloadEventType.STARTED, event)

    def _on_bulk_download_progress(self, event: ProgressEventArgs):
        """Callback for bulk download progress (runs in worker thread)."""
        # Update individual progress and total size under lock
        with self._bulk_progress_lock:
            previous_size = self._bulk_active_progress[event.url]
            size_diff = event.downloaded - previous_size
            self._bulk_active_progress[event.url] = event.downloaded
            self._bulk_total_downloaded_size += size_diff # More efficient total tracking
            # Get latest counts for info text construction
            current_info_text = self._get_bulk_progress_info()

        # Update the shared progress bar (UI update, might need main thread if using GUI toolkit)
        if self.progress:
             self.progress.info_text = current_info_text # Update info text frequently

        self._fire_event(DownloadEventType.PROGRESS, event)

    def _on_bulk_download_complete(self, event: DownloadCompleteEvent):
        """Callback for bulk download completion (runs in worker thread)."""
        with self._bulk_progress_lock:
            self._report_data.append(_DownloadReport(event.filename, event.filesize, ReportReason.COMPLETED, event.url))
            self._success_count += 1
            # Remove completed download from active progress tracking
            if event.url in self._bulk_active_progress:
                 # Add any remaining size difference (though should be minimal at complete)
                 # self._bulk_total_downloaded_size += event.filesize - self._bulk_active_progress[event.url]
                 del self._bulk_active_progress[event.url]
        self._fire_event(DownloadEventType.COMPLETED, event)

    def _on_bulk_download_failed(self, event: DownloadFailureEvent):
        """Callback for bulk download failure (runs in worker thread)."""
        with self._bulk_progress_lock:
             filename_or_url = event.filepath if event.filepath else event.url
             self._report_data.append(_DownloadReport(filename_or_url, 0, ReportReason.FAILED, event.url))
             self._failure_count += 1
             # Remove failed download from active progress tracking
             if event.url in self._bulk_active_progress:
                  del self._bulk_active_progress[event.url]
        self._fire_event(DownloadEventType.FAILED, event)

    def _on_bulk_download_skip(self, event: DownloadSkipEvent):
        """Callback for bulk download skip (runs in worker thread)."""
        with self._bulk_progress_lock:
            self._report_data.append(_DownloadReport(event.filename, 0, ReportReason.SKIPPED, event.url))
            self._skip_count += 1
            # Remove skipped download from active progress tracking
            if event.url in self._bulk_active_progress:
                del self._bulk_active_progress[event.url]
        self._fire_event(DownloadEventType.SKIPPED, event)


    # --- Progress Bar Renderers ---

    @staticmethod
    def _get_basic_colored_text(text: str, percentage: float):
        """Helper for consistent progress bar coloring."""
        return ColorfulProgress.get_basic_colored_text(text, percentage)

    def _get_bulk_progress_info(self) -> str:
        """Constructs the info text string for bulk downloads (needs lock acquired outside)."""
        # Assumes lock is held when called
        downloaded_str = f"{self._downloaded_count}".zfill(len(str(self._total_download_count)))
        file_progress_text = f'⟪ Files: {downloaded_str}/{self._total_download_count} ⟫'
        # Use the efficiently tracked total size
        size_text = FileUtils.get_readable_file_size(self._bulk_total_downloaded_size)
        size_progress_text = f'⟪ Size: {size_text} ⟫'
        return f'{file_progress_text} {size_progress_text}'

    @staticmethod
    def _map_reason_to_event_type_text(reason: ReportReason) -> str:
        """Maps ReportReason enum to display text for report status."""
        if reason == ReportReason.COMPLETED:
            return "Completed"
        if reason == ReportReason.FAILED:
            return "Failed"
        if reason == ReportReason.SKIPPED:
            return "Skipped"
        return "Unknown"

    # Default renderer implementations (can be overridden by user)
    def _info_separator_renderer(self, args: InfoSeparatorRendererArgs) -> str:
        return self._get_basic_colored_text(" | ", args.percentage)

    def _info_text_renderer(self, args: InfoTextRendererArgs) -> str:
        """Renderer for the info text part of the progress bar."""
        # Basic info text (progress value or custom text)
        info_text = self._get_basic_colored_text(args.text, args.percentage)

        # Add success/failure/skip counts for bulk downloads
        # Check if total_download_count > 0 to infer bulk mode context
        if self._total_download_count > 0:
            separator = self._get_basic_colored_text(" | ", args.percentage)
            # Acquire lock to safely read counts for display
            with self._bulk_progress_lock:
                success_count = self._success_count
                failure_count = self._failure_count
                skip_count = self._skip_count

            # <<< MODIFICATION START >>>
            # Add symbols next to counts
            successful_text = Colorizer.colorize(f'✔ {success_count}', '#9acd32') # Green check + count
            failed_text = Colorizer.colorize(f'✖ {failure_count}', '#FF0000')      # Red X + count
            skipped_text = Colorizer.colorize(f'≫ {skip_count}', '#777777')       # Gray >> + count

            # Assemble status text without S:/F:/K: labels
            status_text = str.format("{}{}{}{}{}{}{}",
                                     self._get_basic_colored_text("⟪ ", args.percentage), successful_text,
                                     self._get_basic_colored_text(" ◆ ", args.percentage), # Separator inside
                                     failed_text,
                                     self._get_basic_colored_text(" ◆ ", args.percentage), # Separator inside
                                     skipped_text,
                                     self._get_basic_colored_text(" ⟫", args.percentage))
            # <<< MODIFICATION END >>>

            full_info_text = f"{info_text}{separator}{status_text}"
            return full_info_text
        else:
             # Default for single download or if counts aren't available
             return info_text


    @staticmethod
    def _label_renderer(args: LabelRendererArgs) -> str:
        """Renderer for the label part of the progress bar."""
        label = args.label if args.label else "Progress:" # Default label
        if args.percentage < 100:
            return Colorizer.colorize(label, '#FFCC75')
        return Colorizer.colorize('Completed: ', '#0EB33B') # Change label on completion


    # --- Report Generation ---

    def _print_report(self):
        """Generates and prints the final download report grid."""
        if not self._report_data:
            Printer.info("No download activity to report.")
            return

        grid_data_items: list[_DownloadReportGridData] = []
        row_index = 1
        # Process reports grouped by reason
        for reason in [ReportReason.COMPLETED, ReportReason.FAILED, ReportReason.SKIPPED]:
            # Access report data under lock if necessary, though reading might be okay if append is atomic
            # For safety, copy list if worried about modification during iteration (unlikely here)
            with self._bulk_progress_lock:
                 reports_for_reason = [r for r in self._report_data if r.reason == reason]

            for report in reports_for_reason:
                # Determine filename/extension based on success/failure
                if report.reason == ReportReason.COMPLETED:
                     filename, ext = os.path.splitext(report.filename)
                     display_name = report.filename
                     filesize_str = FileUtils.get_readable_file_size(report.filesize)
                else: # Failed or Skipped
                     # Use URL for display name if filename is empty or not applicable
                     display_name = report.filename if report.filename else report.url
                     # Try to get extension from URL for failed/skipped if possible
                     try:
                          path_part = urllib.parse.urlparse(report.url).path
                          _, ext = os.path.splitext(path_part)
                     except Exception:
                          ext = "" # Cannot determine extension
                     filesize_str = "N/A" # Filesize not applicable or unknown

                grid_data_items.append(
                    _DownloadReportGridData(
                         ext = ext[1:] if ext else "", # Remove leading dot
                         filename_or_url = display_name,
                         filesize_str = filesize_str,
                         row_index = row_index,
                         status = report.reason # Pass reason directly
                     )
                )
                row_index += 1


        # Define Grid Columns
        grid_columns: List[ColumnSettings] = [
            ColumnSettings(title='#', alignment=Alignment.RIGHT, wrap=False,
                           renderer=lambda args: Colorizer.colorize(str(args.cell), '#FFCC75')), # Ensure cell is str
            ColumnSettings(title='Filename/URL', wrap=False, renderer=self._report_grid_file_column_cell_renderer),
            ColumnSettings(title='Type', alignment=Alignment.CENTER, width=6, # Give Type a fixed width
                           renderer=self._report_grid_file_type_column_cell_renderer),
            ColumnSettings(title='Size', alignment=Alignment.RIGHT, width=12, # Give Size a fixed width
                           renderer=self._report_grid_size_column_cell_renderer), # Specific renderer for size
            ColumnSettings(title='Status', alignment=Alignment.CENTER, width=10, # Give Status a fixed width
                           renderer=self._report_grid_status_column_cell_renderer) # Specific renderer for status
        ]

        # Prepare data rows for the grid
        grid_data_rows: List[List[str]] = []
        for item in grid_data_items:
            grid_data_rows.append([
                str(item.row_index),
                item.filename_or_url,
                item.ext,
                item.filesize_str,
                self._map_reason_to_event_type_text(item.status) # Map reason to text
            ])

        # Create and print the grid
        grid = Grid(grid_columns, grid_data_rows)
        grid.border_style = BorderStyle.SINGLE
        grid.border_color = '#FFCC75'
        # grid.cell_renderer = self._report_grid_cell_renderer # Can set a default, but column renderers override
        print(os.linesep)
        # grid.fill_screen() # Optional: uncomment to make grid fill terminal width
        grid.print()

    # --- Report Grid Cell Renderers ---

    def _report_grid_status_column_cell_renderer(self, args: CellRendererArgs) -> str:
        """Renderer for the status column cells."""
        if args.is_header: return Colorizer.colorize(args.cell, '#FFCC75', bold=True)
        if args.cell == 'Failed': return Colorizer.colorize(args.cell, '#FF0000')
        if args.cell == 'Skipped': return Colorizer.colorize(args.cell, '#777777')
        if args.cell == 'Completed': return Colorizer.colorize(args.cell, '#0EB33B')
        return args.cell # Default

    def _report_grid_size_column_cell_renderer(self, args: CellRendererArgs) -> str:
         """Renderer for the filesize column cells."""
         if args.is_header: return Colorizer.colorize(args.cell, '#FFCC75', bold=True)
         # Colorize based on size unit
         size_text = str(args.cell)
         if size_text.endswith(" KB"): return Colorizer.colorize(size_text, '#00a9ff')
         if size_text.endswith(" MB"): return Colorizer.colorize(size_text, '#d2309a')
         if size_text.endswith(" GB"): return Colorizer.colorize(size_text, '#fbb315')
         # Add TB and PB if desired
         if size_text.endswith(" TB"): return Colorizer.colorize(size_text, '#8D7BA3') # Example color
         if size_text.endswith(" PB"): return Colorizer.colorize(size_text, '#ED4F74') # Example color
         if size_text.endswith(" B"): return Colorizer.colorize(size_text, '#aaaaaa')
         if size_text == "N/A": return Colorizer.colorize(size_text, '#777777')
         return size_text # Default

    def _report_grid_file_column_cell_renderer(self, args: CellRendererArgs) -> str:
        """Renderer for the filename/URL column cells."""
        if args.is_header: return Colorizer.colorize(args.cell, '#FFCC75', bold=True)
        # Colorize based on file extension derived from the display name
        _ , ext = os.path.splitext(args.cell)
        color = self._file_color_scheme.get(ext[1:].lower() if ext else "", '#FFFFFF') # Use white default
        return Colorizer.colorize(args.cell, color)

    def _report_grid_file_type_column_cell_renderer(self, args: CellRendererArgs) -> str:
        """Renderer for the file type (extension) column cells."""
        if args.is_header: return Colorizer.colorize(args.cell, '#FFCC75', bold=True)
        ext_lower = str(args.cell).lower()
        color = self._file_color_scheme.get(ext_lower, '#FFFFFF') # Use white default
        # Make extension uppercase for display consistency maybe?
        return Colorizer.colorize(args.cell.upper(), color)