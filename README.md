A simple package containing various command-line utilities.

## Table of Contents
- [Caution](#caution)
- [Installation](#installation)
- [Utilities](#contents)
  - [Grid](#grid)
  - [Printer](#printer)
  - [Progress](#progress)


## Caution

**This package does not have any tests. It is not recommended to use it in production.
I wrote this package for my own personal use. I don't have any immediate plans to add tests and make it production-ready.
Use it at your own risk.**

## Installation

```bash
  pip install mizue
```

## Utilities (Work in Progress)
- [Grid](#grid)
- [Printer](#printer)
- [Progress](#progress)
- More utilities coming soon...


### Grid

This class can be used to print a table/grid in the terminal.

```python
from mizue.printer.grid import Grid, ColumnSettings, Alignment
from mizue.file import FileUtils
import os

column2 = ColumnSettings(title='File', alignment=Alignment.RIGHT)
column3 = ColumnSettings(title='Size', alignment=Alignment.CENTER, width=50)
columns = [column2, column3]


filelist = FileUtils.list_files(".", recursive=True, fullpath=True)
grid_data = list(map(lambda f: [f, FileUtils.get_readable_file_size(os.stat(f).st_size)], filelist))
grid = Grid(columns, grid_data)
grid.print()
```

`ColumnSettings` allows the following attributes to be set:
- `title`: The title of the column
- `alignment`: The alignment of the column. Can be one of the following: 
  - ``Alignment.LEFT`` 
  - ``Alignment.CENTER`` 
  - ``Alignment.RIGHT``
- `width`: The width of the column
- `renderer`: A function that takes in an object of type ``CellRendererArgs`` and returns a string to be displayed in the column.

`Grid` allows the following attributes to be set:
- `border_color`: The color of the border in hex format
- `border_style`: The style of the border. Can be one of the following: 
  - ``BorderStyle.SINGLE`` 
  - ``BorderStyle.DOUBLE`` 
  - ``BorderStyle.BASIC`` 
  - ``BorderStyle.NONE``
- `cell_renderer`: A function that takes in an object of type ``CellRendererArgs`` and returns a string to be displayed in the cell.

### Printer

This class contains various static methods for printing text in different colors.

```python
from mizue.printer import Printer

Printer.print('Hello World!', '#ff0000')
Printer.print('Hello World!', (255, 0, 0))
```

Following is a list of some of the methods available in this class:
- `print(text, text_color, background_color=None, bold=False, underline=False)`
- `error(text)`
- `warning(text)`
- `info(text)`
- `success(text)`

Using the `colorize` method from `Colorizer` class, you can format a text and use it later. For example:

```python
from mizue.printer import Colorizer
colored_text = Colorizer.colorize('Hello World!', '#ff0000')
print(colored_text)
```


### Progress

This is a simple class for displaying progress bars in the terminal.

```python
from mizue.progress import Progress
from time import sleep

progress = Progress(0, 1200, 0) # (start, end, current)
progress.label = 'Progress: ' # This text is displayed before the progress bar
progress.info_text = '(in progress)' # This text is displayed after the progress bar
progress.start()

for i in range(1200):
  progress.update_value(i)
  sleep(0.01)

progress.stop()
```

Progress allows the following attributes to be set:
- `info_separator`: The character to be used to separate the info text from the progress bar
- `info_separaotr_renderer`: A function that takes in an object of type ``InfoSeparatorRendererArgs`` and returns a string to be used to separate the info text from the progress bar
- `info_text`: Text to be displayed after the progress bar
- `info_text_renderer`: A function that takes in an object of type ``InfoTextRendererArgs`` and returns a string to be displayed after the progress bar
- `label`: Text to be displayed before the progress bar
- `label_renderer`: A function that takes in an object of type ``LabelRendererArgs`` and returns a string to be displayed before the progress bar
- `progress_bar_renderer`: A function that takes in an object of type ``ProgressBarRendererArgs`` and returns a string to be displayed as the progress bar
- `percentage_renderer`: A function that takes in an object of type ``PercentageRendererArgs`` and returns a string to be displayed as the percentage
- `spinner_renderer`: A function that takes in an object of type ``SpinnerRendererArgs`` and returns a string to be displayed as the spinner

An example of rendering a custom label (appears before the progress bar):

```python
from mizue.progress import Progress
from mizue.progress import LabelRendererArgs
from mizue.printer import Colorizer
from time import sleep

def label_renderer(args: LabelRendererArgs) -> str:
  return Colorizer.colorize(args.label, '#ff0000') \
    if args.percentage < 50 \ 
    else Colorizer.colorize(args.label, '#00ff00')

progress = Progress(0, 1200, 0)
progress.label_renderer = label_renderer
progress.start()

for i in range(1200):
  progress.update_value(i)
  sleep(0.1)

progress.stop()
```