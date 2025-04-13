import os
import re
import time
import urllib.parse
import uuid
from typing import Callable, Optional

import requests
from pathvalidate import sanitize_filename

from mizue.util import EventListener
from .download_event import (DownloadEventType, DownloadFailureEvent,
                             DownloadCompleteEvent, DownloadStartEvent,
                             ProgressEventArgs, DownloadSkipEvent)
from .download_metadata import DownloadMetadata
from .progress_data import ProgressData


class Downloader(EventListener):
    """Handles downloading single files with progress events and retries."""

    def __init__(self):
        super().__init__()
        self._alive = True

        self.force_download: bool = False
        """Whether to force the download even if the file already exists"""

        self.output_path: str = "."
        """Default output path if not specified in download method"""

        self.retry_count: int = 3 # Reduced default, maybe 3 is enough?
        """The number of times to retry the download on specific errors"""

        self.retry_delay: float = 1.0 # Seconds to wait between retries
        """Delay in seconds between retries"""

        self.timeout: int = 10
        """The timeout in seconds for the connection"""

        self.chunk_size: int = 1024 * 8 # Increased default chunk size to 8KB
        """Chunk size for downloading file content"""

        self.user_agent: str = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/91.0.4472.124 Safari/537.36') # Example modern UA
        """User agent string to use for requests"""

    def close(self):
        """
        Signals the downloader to stop any ongoing downloads gracefully.
        Downloads might take a moment to fully stop iterating chunks.
        """
        self._alive = False

    def open(self):
        """
        Resets the downloader's alive status, allowing new downloads
        if it was previously closed.
        """
        self._alive = True

    def download(self, url: str, output_path: Optional[str] = None):
        """
        Downloads a file from a URL.

        Args:
            url: The URL to download from.
            output_path: The directory to save the file in. If None, uses self.output_path.
        """
        if not self._alive:
            print("Downloader is closed. Call open() before downloading.") # Or raise an error
            return

        path_to_save = output_path if output_path is not None else self.output_path
        if not path_to_save: # Ensure path_to_save is never empty
             path_to_save = "."

        try:
            # Use response as context manager for automatic connection closing
            with self._get_response(url) as response:
                # Check for HTTP errors immediately after getting response
                response.raise_for_status() # Raises HTTPError for 4xx/5xx

                metadata = self._get_download_metadata(response, path_to_save)

                if not os.path.exists(metadata.filepath) or self.force_download:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(metadata.filepath), exist_ok=True)
                    self._download_content(response, metadata)
                else:
                    self._fire_event(DownloadEventType.SKIPPED, DownloadSkipEvent(
                        url=metadata.url,
                        filename=metadata.filename,
                        filepath=metadata.filepath,
                        reason="File already exists"
                    ))

        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx) specifically
            self._fire_failure_event(url, e.response, exception=e)
        except requests.exceptions.RequestException as e:
            # Handle other requests errors (ConnectionError, Timeout, etc.)
             # Response might be None here if request failed before response received
            self._fire_failure_event(url, getattr(e, 'response', None), exception=e)
        except Exception as e:
             # Catch potential other errors (e.g., filesystem errors)
            self._fire_failure_event(url, None, exception=e)


    def _get_response(self, url: str) -> requests.Response:
        """Initiates the request, handles retries, and returns the response object."""
        headers = {'User-Agent': self.user_agent}
        last_exception = None

        for attempt in range(self.retry_count + 1):
            if not self._alive:
                 raise Exception("Download cancelled by user") # Or a custom exception

            try:
                response = requests.get(url, stream=True, timeout=self.timeout, headers=headers, allow_redirects=True)
                # Check for specific retryable status codes if needed, e.g.:
                # if response.status_code in {503, 504} and attempt < self.retry_count:
                #    raise requests.exceptions.RetryError("Retryable status code") # Custom trigger for retry
                return response # Return successful response immediately
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1)) # Exponential backoff optional
                    continue # Retry
                else:
                    raise # Raise the exception after final retry fails
            except requests.exceptions.RequestException as e:
                 # Non-retryable request errors (like invalid URL)
                 last_exception = e
                 raise # Raise immediately

        # Should not be reached if loop logic is correct, but raise last error if it is
        raise last_exception or Exception("Failed to get response after retries")


    def _download_content(self, response: requests.Response, metadata: DownloadMetadata):
        """Handles writing the file content and firing progress events."""
        try:
            # Fire STARTED event
            self._fire_event(DownloadEventType.STARTED, DownloadStartEvent(
                url=metadata.url,
                filename=metadata.filename,
                filepath=metadata.filepath,
                filesize=metadata.filesize,
            ))

            downloaded = 0
            last_percent = -1
            with open(metadata.filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if not self._alive:
                        # Ensure file is closed before attempting removal
                        f.close()
                        # Attempt cleanup on cancellation
                        try:
                             if os.path.exists(metadata.filepath):
                                  os.remove(metadata.filepath)
                        except OSError as e_os:
                             # Log cleanup failure if necessary
                             print(f"Warning: Could not remove partial file '{metadata.filepath}': {e_os}")
                        # Fire failure event for cancellation
                        self._fire_failure_event(metadata.url, response, exception=Exception("Download cancelled"), filepath=metadata.filepath)
                        return # Exit download function

                    # chunk is guaranteed to be bytes if stream=True
                    chunk_size = len(chunk)
                    if chunk_size > 0:
                         f.write(chunk)
                         downloaded += chunk_size

                    # Throttle progress updates slightly if needed, e.g., only on percentage change
                    if metadata.filesize > 0: # Avoid division by zero
                        percent = int((downloaded / metadata.filesize) * 100)
                        if percent != last_percent: # Update only when percentage changes
                             self._fire_event(DownloadEventType.PROGRESS, ProgressEventArgs(
                                 downloaded=downloaded,
                                 percent=percent,
                                 filename=metadata.filename,
                                 filepath=metadata.filepath,
                                 filesize=metadata.filesize,
                                 url=metadata.url,
                             ))
                             last_percent = percent
                    # else: handle case with unknown filesize if needed


            # Ensure final progress event is sent if download completes fully
            if self._alive:
                # Send 100% progress if not already sent
                if last_percent != 100 and metadata.filesize > 0 :
                    self._fire_event(DownloadEventType.PROGRESS, ProgressEventArgs(
                        downloaded=metadata.filesize, # Assume full download if loop finished
                        percent=100,
                        filename=metadata.filename,
                        filepath=metadata.filepath,
                        filesize=metadata.filesize,
                        url=metadata.url,
                    ))
                # Fire COMPLETED event
                self._fire_event(DownloadEventType.COMPLETED, DownloadCompleteEvent(
                    url=metadata.url,
                    filename=metadata.filename,
                    filepath=metadata.filepath,
                    filesize=metadata.filesize, # Use actual downloaded or header filesize? Header is safer.
                ))

        except Exception as e:
            # Catch errors during file writing or chunk iteration
            self._fire_failure_event(metadata.url, response, exception=e, filepath=metadata.filepath)
            # Re-raise the exception after firing the event
            raise


    def _fire_failure_event(self, url: str, response: Optional[requests.Response],
                            exception: Optional[BaseException], filepath: Optional[str] = None):
        """Helper to fire the FAILED event."""
        status_code = response.status_code if response is not None else None
        reason = response.reason if response is not None else "Request Failed"
        if exception and not reason : reason = str(exception)

        self._fire_event(DownloadEventType.FAILED, DownloadFailureEvent(
            url=url,
            status_code=status_code,
            reason=reason,
            exception=exception,
            filepath=filepath,
        ))


    def _get_download_metadata(self, response: requests.Response, output_path: str) -> DownloadMetadata:
        """Extracts filename, filepath, and filesize."""
        filename = self._get_filename(response)
        if not filename:
             # Generate a fallback filename if none could be determined
             parsed_url = urllib.parse.urlparse(response.url)
             fallback = os.path.basename(parsed_url.path) or f"download_{uuid.uuid4()}"
             filename = sanitize_filename(fallback)


        filepath = os.path.join(output_path, filename)
        # Get filesize, default to 0 if not present (safer than 1 for percentage calc)
        filesize = int(response.headers.get("Content-Length", 0))

        return DownloadMetadata(
            filename=filename,
            filepath=filepath,
            filesize=filesize,
            url=response.url,
            uuid=str(uuid.uuid4()) # Unique ID for this specific download attempt
        )


    @staticmethod
    def _get_filename(response: requests.Response) -> Optional[str]:
        """Extracts filename from Content-Disposition or URL."""
        filename = None
        # Try requests utility first for potentially better Content-Disposition parsing
        try:
            from requests.utils import get_filename_from_cd
            cd_filename = get_filename_from_cd(response.headers.get('content-disposition'))
            if cd_filename:
                 filename = sanitize_filename(cd_filename) # Sanitize immediately
        except ImportError:
             # Fallback to manual parsing if requests.utils is not available (unlikely)
             content_disposition = response.headers.get('content-disposition')
             if content_disposition:
                  # Simple regex, might miss complex cases like filename*
                  match = re.search(r'filename\*?=(?:UTF-8\'\')?([^;\n"\']+|\"[^"]*\"|\'[^"]*\')', content_disposition, flags=re.IGNORECASE)
                  if match:
                       fname_part = match.group(1).strip('"\' ')
                       # Basic unquoting, full URL decoding might be needed for filename*
                       filename = sanitize_filename(urllib.parse.unquote(fname_part))

        # Fallback to URL if filename still not found
        if not filename:
            try:
                 parsed_url = urllib.parse.urlparse(response.url)
                 path_filename = os.path.basename(parsed_url.path)
                 if path_filename:
                      filename = sanitize_filename(urllib.parse.unquote(path_filename))
            except Exception:
                 pass # Ignore errors during URL parsing fallback

        return filename if filename else None # Return None if no filename found