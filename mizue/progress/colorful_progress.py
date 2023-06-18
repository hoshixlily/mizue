from .progress_renderer_args import LabelRendererArgs, PercentageRendererArgs, ProgressBarRendererArgs, \
    SpinnerRendererArgs
from .progress import Progress
from ..printer import Printer


class ColorfulProgress(Progress):
    def __init__(self, start: int = 0, end: int = 100, value: int = 0):
        super().__init__(start, end, value)
        self._setup_renderers()

    @staticmethod
    def get_basic_colored_text(text: str, percentage: float):
        if percentage < 15:
            return Printer.format_hex(text, '#FF0D0D')
        elif percentage < 30:
            return Printer.format_hex(text, '#FF4E11')
        elif percentage < 45:
            return Printer.format_hex(text, '#FF8E15')
        elif percentage < 60:
            return Printer.format_hex(text, '#FAB733')
        elif percentage < 75:
            return Printer.format_hex(text, '#ACB334')
        elif percentage < 90:
            return Printer.format_hex(text, '#69B34C')
        else:
            return Printer.format_hex(text, '#0EB33B')

    @staticmethod
    def _label_renderer(args: LabelRendererArgs):
        if args.percentage < 100:
            return Printer.format_hex(args.label, '#FFCC75')
        return Printer.format_hex(args.label, '#0EB33B')

    @staticmethod
    def _percentage_renderer(args: PercentageRendererArgs):
        return ColorfulProgress.get_basic_colored_text("{:.2f}%".format(args.percentage), args.percentage)

    @staticmethod
    def _progress_renderer(args: ProgressBarRendererArgs):
        return ColorfulProgress.get_basic_colored_text(args.text, args.percentage)

    @staticmethod
    def _spinner_renderer(args: SpinnerRendererArgs):
        return ColorfulProgress.get_basic_colored_text(args.spinner, args.percentage)

    def _setup_renderers(self):
        self.label_renderer = lambda args: self._label_renderer(args)  # LabelRendererArgs
        self.percentage_renderer = lambda args: self._percentage_renderer(args)  # PercentageRendererArgs
        self.progress_bar_renderer = lambda args: self._progress_renderer(args)  # ProgressBarRendererArgs
        self.spinner_renderer = lambda args: self._spinner_renderer(args)  # SpinnerRendererArgs
        self.info_text_renderer = lambda args: self._info_text_renderer(args.text)  # InfoTextRendererArgs
        self.info_separator_renderer = lambda args: self._info_separator_renderer()  # InfoSeparatorRendererArgs
