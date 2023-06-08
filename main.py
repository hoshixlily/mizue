from mizue.printer import Printer, TerminalColors


def print_message(name):
    Printer.prevent_newline(True)
    Printer.error(f'Hi, {name}. ')
    Printer.print(f'How are you?', TerminalColors.YELLOW)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.print('This is a test', TerminalColors.RED, True, True)
    Printer.print('This is a test', TerminalColors.BG_CYAN, True, True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_message('Mizu')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
