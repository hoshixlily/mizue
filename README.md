A simple package containing various command-line utilities.

## Installation

```bash
  pip install mizue
```

## Usage

### Printer

```python
from mizue.printer import Printer, TerminalColors as Color

Printer.print_ansi("Hello World!")
Printer.print_ansi("Hello World!", Color.RED)
Printer.print_ansi("Hello World!", Color.RED, bold=True, underlined=True)
```
The ``Printer`` class is a simple wrapper around the ``print`` function. It allows you to print colored text to the terminal. The ``TerminalColors`` class contains a list of colors that can be used with the ``Printer`` class.
The ``Printer`` class also provides the following methods:
```python
from mizue.printer import Printer, TerminalColors as Color
Printer.error("Hello World!")
Printer.warning("Hello World!")
Printer.success("Hello World!")
Printer.info("Hello World!")
```

It is possible to prevent the new line character from being printed at the end of the line:

```python
from mizue.printer import Printer, TerminalColors as Color

Printer.prevent_newline(True)
Printer.print_ansi("Hello World!", Color.RED)
```