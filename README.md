A simple package containing various command-line utilities.

## Table of Contents
- [Caution](#caution)
- [Installation](#installation)
- [Utilities](#contents)
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
- [Printer](#printer)
- [Progress](#progress)
- More utilities coming soon...

### Printer

This class contains various static methods for printing text in different colors.

```python
from mizue.printer import Printer

Printer.print_hex('Hello World!', '#ff0000')
Printer.print_rgb('Hello World!', (255, 0, 0))
```

Following is a list of some of the methods available in this class:
- `format_hex(text, text_color, background_color=None, bold=False, underline=False)`
- `format_rgb(text, rgb_color, background_color=None, bold=False, underline=False)`
- `print_hex(text, text_color, background_color=None, bold=False, underline=False)`
- `print_rgb(text, rgb_color, background_color=None, bold=False, underline=False)`
- `error(text)`
- `warning(text)`
- `info(text)`
- `success(text)`

Using the `format_*` methods, you can format text and use it later. For example:

```python
from mizue.printer import Printer
colored_text = Printer.format_hex('Hello World!', '#ff0000')
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
from mizue.printer import Printer
from time import sleep

def label_renderer(args: LabelRendererArgs) -> str:
  return Printer.format_hex(args.label, '#ff0000') \
    if args.percentage < 50 \ 
    else Printer.format_hex(args.label, '#00ff00')

progress = Progress(0, 1200, 0)
progress.label_renderer = label_renderer
progress.start()

for i in range(1200):
  progress.update_value(i)
  sleep(0.1)

progress.stop()
```