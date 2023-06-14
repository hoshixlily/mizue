import os.path
import signal
import sys
from time import sleep

from mizue.network.downloader import Downloader, ProgressEventArgs, DownloadEvent
# from mizue.network.downloader.downloader import Downloader
from mizue.printer import Printer, TerminalColors
from mizue.progress import Progress
from mizue.util import Utility


class SignalHandler:
    def __init__(self, progress_instance: Progress):
        self._signal_received = False
        self._progress = progress_instance

    def __call__(self, sig, frame):
        self._signal_received = True
        self._progress.terminate()

    def is_signal_received(self):
        return self._signal_received


def print_message(name):
    Printer.prevent_newline(True)
    Printer.error(f'Hi, {name}. ')
    Printer.print_ansi(f'How are you?', TerminalColors.YELLOW)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.print_ansi('This is a test', TerminalColors.RED, True, True)
    Printer.print_ansi('This is a test', TerminalColors.BG_CYAN, True, True)
    Printer.info(f'Terminal width: {Utility.get_terminal_width()}')
    Printer.info(f'Terminal height: {Utility.get_terminal_height()}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    progress = Progress(0, 100, 0, 10)
    signal.signal(signal.SIGINT, SignalHandler(progress))

    # print_message('Mizu')
    #
    # interval = 0.1
    # # progress.set_update_interval(interval)
    # progress.start()
    # progress.set_label('Progress: ')
    # for i in range(101):
    #     progress.set_info(f'File {i} of 100')
    #     progress.update_value(i)
    #     sleep(interval)
    # progress.stop()

    # print files
    # files = FileUtils.list_files(sys.argv[1], True, True)
    # # files = FileUtils.list_files("X:\\Images\\Ladies\\Flickr\\Chingcho Chang (chingcho)", True, False)[0:]
    # table = list(map(lambda f: [f, FileUtils.get_readable_file_size(os.stat(f).st_size)], files))
    # # table_printer = TablePrinter([[files[-1]]])
    # table_printer = TablePrinter(table)
    # table_printer.color_list = ['#00a86b', '#FFD42B', '#32CD32']
    # table_printer.border_color = '#348f50'
    # table_printer.border_style = BorderStyle.SINGLE
    # table_printer.cell_length_list = []
    # # table_printer.title_data = [Printer.format_hex('Path', '#906090'), Printer.format_hex('Name', '#901433')]
    # table_printer.title_data = ['File', 'Size']
    # table_printer.align_list = [Alignment.LEFT, Alignment.RIGHT]
    # table_printer.enumerated = True
    # table_printer.enumeration_color = '#ffcc75'
    # # table_printer.enumeration_title = 'Order'
    # table_printer.print()
    #
    # Printer.print_rgb(' RGB COLORED TEXT ', (255, 220, 110), bold=True, underlined=False)
    # Printer.print_hex(' HEX COLORED TEXT ', '#00a9ff', bold=True, underlined=False)
    # Printer.print_ansi(' ANSI COLORED TEXT ', TerminalColors.BRIGHT_GREEN, bold=True, underlined=False)
    #
    # Printer.print_rgb(' RGB COLORED TEXT WITH BG COLOR ', (0, 0, 0), (255, 224, 142), bold=True, underlined=False)
    # Printer.print_rgb(' RGB COLORED TEXT WITH BG COLOR ', (0, 0, 0), (255, 224, 142), bold=True, underlined=False)
    #
    # text = f'{Printer.format_hex(" COLORED ", "#212326", "#ffcc75", bold=True)} {Printer.format_hex("T", "#00a86b")}{Printer.format_hex("E", "#00a9ff")}{Printer.format_hex("X", "#CC5590")}{Printer.format_hex("T", "#8090aa")}'
    # # TablePrinter.print_text_with_border(text, border_color='#Ffcc75', border_style=TablePrinter.BorderStyle.SINGLE)
    #
    # # Printer.print_hex(str(table_printer._is_cjk('마')), '#FFCC75')

    downloader = Downloader()
    # downloader.download(url=sys.argv[1], output_path='.')
    pea: ProgressEventArgs = None
    progress_event_id = downloader.add_event(DownloadEvent.PROGRESS, lambda p: Printer.print_hex(f"Progress: {p}", '#906090') if p["percent"] % 10 == 0 else None)
    complete_event_id = downloader.add_event(DownloadEvent.COMPLETED, lambda: Printer.print_hex("Download completed", '#00a86b'))
    downloader.no_progress = True
    # downloader.download(url='https://files.yande.re/image/9b89ddde16b79b585bbfa23e3a274ef1/yande.re%201030222%20bodysuit%20cyberpunk%3A_edgerunners%20cyberpunk_2077%20lucy_%28cyberpunk%29%20no_bra%20possible_duplicate%20ringeko-chan%20see_through%20smoking%20undressing.jpg', output_path='.')
    # downloader.remove_event(progress_event_id)
    # downloader.remove_event(complete_event_id)
    #
    # downloader.download(url='https://files.yande.re/image/9b89ddde16b79b585bbfa23e3a274ef1/yande.re%201030222%20bodysuit%20cyberpunk%3A_edgerunners%20cyberpunk_2077%20lucy_%28cyberpunk%29%20no_bra%20possible_duplicate%20ringeko-chan%20see_through%20smoking%20undressing.jpg', output_path='.')

    download_list = [
        "https://files.yande.re/image/33ef48f08e73a28119604af0ac088fb4/yande.re%201060754%20sweater%20yuga-.png",
        "https://files.yande.re/image/c8b6aa0caa49efc0659e54875acdede9/yande.re%201096733%20admire_vega_%28umamusume%29%20animal_ears%20starheart%20sweater%20tail%20uma_musume_pretty_derby.png",
        # "https://files.yande.re/image/d0a14bf59290198ace01814ef5785dd4/yande.re%201088490%20dress%20garter%20heels%20honkai%3A_star_rail%20kafka_%28honkai%3A_star_rail%29%20no_bra%20ringeko-chan.png",
        # "https://files.yande.re/image/9b0bec0f5d184601d86604d5505e0ef7/yande.re%201081437%20garter%20genshin_impact%20heels%20leotard%20mona_megistus%20no_bra%20pantyhose%20ringeko-chan%20witch.png",
        # "https://files.yande.re/image/dd05512a918ebb656f344af0d93865c9/yande.re%201063719%20dress%20genshin_impact%20mona_megistus%20no_bra%20pantsu%20ringeko-chan%20thighhighs%20witch.png",
        # "https://files.yande.re/image/2e67be61ede46489f6be3013e7447418/yande.re%201042616%20animal_ears%20dress%20genshin_impact%20kitsune%20ringeko-chan%20thighhighs%20yae_miko.jpg",
        # "https://files.yande.re/image/9b89ddde16b79b585bbfa23e3a274ef1/yande.re%201030222%20bodysuit%20cyberpunk%3A_edgerunners%20cyberpunk_2077%20lucy_%28cyberpunk%29%20no_bra%20possible_duplicate%20ringeko-chan%20see_through%20smoking%20undressing.jpg",
        # "https://files.yande.re/image/335292c9ce0fe7e4bd7bbee7960d8f9e/yande.re%201023284%20heels%20juraku_sachiko%20kakegurui%20pantyhose%20ringeko-chan%20sado_mikura%20seifuku%20thighhighs.png",
        "https://www.hoshilily.com/wp-content/uploads/2021/05/20210501_01.jpg"
    ]
    downloader.download_list(download_list, '.')


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
