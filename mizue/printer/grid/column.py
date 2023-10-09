from mizue.printer.grid import ColumnSettings, Alignment


class Column:
    def __init__(self, settings: ColumnSettings):
        self.alignment = settings["alignment"] if "alignment" in settings else Alignment.LEFT
        self.index: int = 0
        self.renderer = settings["renderer"] if "renderer" in settings else None
        self.title = settings["title"] if "title" in settings else ""
        self.width = settings["width"] if "width" in settings else None
        if self.width is not None and self.width <= 0:
            raise ValueError("The column width must be greater than zero")
        self.wrap = settings["wrap"] if "wrap" in settings else False
