from mizue.printer import Printer, TerminalColors


def print_hi(name):
    Printer.error(f'Hi, {name}')
    Printer.print(f'Hi, {name}', TerminalColors.YELLOW)


if __name__ == '__main__':
    print_hi('Mizue')
