import curses
import os

from user_interface.constants import TEXT_HELP


class Window:
    def __init__(self, file_name, encoding, mode_rainbow=False):
        self._file_name = file_name
        self._file = None
        self._position = 0
        self._position_max = 0
        self._is_end = False
        self._amount_bytes_in_line = 16
        self._amount_lines = 16
        self._char_mode = False
        self._help_shown = False
        self._exception_shown = False
        self._encoding = encoding
        self._text_help_parsed = TEXT_HELP.split('\n')
        self._mode_rainbow = mode_rainbow

        self._padding_left_len = 7

        self._width = 3 + self._padding_left_len + 1 + 3 * \
            self._amount_bytes_in_line + 3
        self._height = 2 + self._amount_lines + 5

        self._stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        self._index_rainbow = -1
        self._colors_amount = 252
        if self._mode_rainbow:
            curses.use_default_colors()
            for i in range(self._colors_amount):
                curses.init_pair(4 + i, i, -1)
            self._index_rainbow = 0

        self._char_quit = 'q'
        self._char_scroll_up = 'w'
        self._char_scroll_down = 's'
        self._char_change_mode = 'm'
        self._char_show_help = 'h'

    def start(self):
        curses.resize_term(self._height, self._width)

        self._file = open(self._file_name, mode='rb')

        self.__print_top()
        self.__print_info()
        self._stdscr.refresh()
        self.__update_board()

        while True:
            try:
                curses.curs_set(0)
                if curses.is_term_resized(self._height, self._width):
                    curses.resize_term(self._height, self._width)
                    self._stdscr.refresh()

                c = self._stdscr.getch()

                if c == ord(self._char_quit):
                    break
                elif c == ord(self._char_scroll_up):
                    if self._help_shown or self._exception_shown:
                        self.__clear_plane()
                    self.__update_board(scroll=-1)
                elif c == 23:
                    if self._help_shown or self._exception_shown:
                        self.__clear_plane()
                    self.__update_board(scroll=-self._amount_lines)
                elif c == ord(self._char_scroll_down):
                    if not self._is_end:
                        if self._help_shown or self._exception_shown:
                            self.__clear_plane()
                        self.__update_board(scroll=1)
                elif c == 19:
                    if not self._is_end:
                        if self._help_shown or self._exception_shown:
                            self.__clear_plane()
                        self.__update_board(scroll=self._amount_lines)
                elif c == ord(self._char_change_mode):
                    self._char_mode = not self._char_mode
                    if not self._help_shown and not self._exception_shown:
                        self.__update_board()
                elif c == ord(self._char_show_help):
                    self.__clear_plane()
                    if not self._help_shown:
                        self.__show_help()
                    else:
                        self.__update_board()
                    self._help_shown = not self._help_shown

                self._exception_shown = False

            except Exception as exception:
                self._exception_shown = True
                self.__clear_plane()
                self.__show_exception(exception)

        self._file.close()

    def __update_board(self, scroll: int = 0):
        if self._position == 0 and scroll < 0:
            return
        self._position += scroll * self._amount_bytes_in_line
        if self._position < 0:
            self._position = 0
        self._position_max = max(self._position, self._position_max)
        self._is_end = False

        _bytes = self.__read(
            self._position, self._amount_lines * self._amount_bytes_in_line)

        for i in range(self._amount_lines):
            hex_repr = hex(self._position + i * self._amount_bytes_in_line)[2:]
            _bytes_current = _bytes[i * self._amount_bytes_in_line:
                                    (i + 1) * self._amount_bytes_in_line]

            if len(_bytes_current) < self._amount_bytes_in_line:
                self._is_end = True
                if len(_bytes_current) == 0:
                    self.__update_board(-1)
                    return

            temp = '0x' + '0' * (self._padding_left_len - len(hex_repr)) + \
                   hex_repr + ' | '
            self._stdscr.addstr(i + 2, 1, temp)

            for _i, b in enumerate(_bytes_current):
                num = Window.__format(b, self._encoding, self._char_mode)
                if self._mode_rainbow:
                    self._stdscr.addstr(
                        i + 2, 1 + len(temp) + 3 * _i, num,
                        curses.color_pair(
                            4 + (self._position +
                                 i * self._amount_bytes_in_line + _i) %
                            self._colors_amount))
                elif b == 0:
                    self._stdscr.addstr(
                        i + 2, 1 + len(temp) + 3 * _i,
                        num, curses.color_pair(2))
                else:
                    self._stdscr.addstr(i + 2, 1 + len(temp) + 3 * _i, num)

            if self._is_end:
                self._stdscr.addstr(
                    i + 2, 1 + len(temp) + 3 * len(_bytes_current),
                    ' ' * (3 * self._amount_bytes_in_line -
                           len(_bytes_current)))
                self._stdscr.addstr(
                    i + 2, self._width - 1, '|')

                for _i in range(i + 1, self._amount_lines):
                    self._stdscr.addstr(
                        _i + 2, 0,
                        ' ' * (3 + self._padding_left_len + 1) + '|' +
                        ' ' * (3 * self._amount_bytes_in_line + 1) + '|')
                break

            else:
                self._stdscr.addstr(
                    i + 2, self._width - 1, '|')

        self._stdscr.addstr(
            self._amount_lines + 2, 0,
            '-' * (3 + self._padding_left_len + 1) + '+' +
            '-' * (3 * self._amount_bytes_in_line + 1) + '+')

    def __show_help(self):
        for i, line in enumerate(self._text_help_parsed):
            attributes = curses.color_pair(3)

            if line.startswith('<bold>'):
                attributes = attributes | curses.A_BOLD
                line = line.replace('<bold>', '')
            if line.startswith('<underline>'):
                attributes = attributes | curses.A_UNDERLINE
                line = line.replace('<underline>', '')

            self._stdscr.addstr(
                2 + i, 3 + self._padding_left_len + 3,
                line, attributes)
        for i in range(len(self._text_help_parsed), self._amount_lines):
            self._stdscr.addstr(
                2 + i, 3 + self._padding_left_len + 3,
                ' ' * (3 * self._amount_bytes_in_line - 1))

    def __clear_plane(self):
        for i in range(self._amount_lines):
            self._stdscr.addstr(
                2 + i, 3 + self._padding_left_len + 3,
                ' ' * (3 * self._amount_bytes_in_line - 1))

    def __print_top(self):
        self._stdscr.addstr(
            0, 1,
            'HexViewer | ' +
            ' '.join(Window.__format(x)
                     for x in range(self._amount_bytes_in_line)) + ' |')
        self._stdscr.addstr(
            1, 0,
            '-' * (3 + self._padding_left_len + 1) + '+' +
            '-' * (3 * self._amount_bytes_in_line + 1) + '+')

    def __print_info(self):
        self._stdscr.addstr(
            self._amount_lines + 2, 0,
            '-' * (3 + self._padding_left_len + 1) + '+' +
            '-' * (3 * self._amount_bytes_in_line + 1) + '+')

        temp_file = f'File{" " * (3 + self._padding_left_len - 4)}| ' \
                    f'{os.path.abspath(self._file_name)}'
        temp_file = temp_file \
            if len(temp_file) < self._width \
            else temp_file[:self._width - 6] + '...'
        self._stdscr.addstr(
            self._amount_lines + 3, 1,
            temp_file + ' ' * (self._width - len(temp_file) - 2) + '|')

        temp_size = f'Size{" " * (3 + self._padding_left_len - 4)}| ' \
                    f'{Window.__format_size(os.path.getsize(self._file_name))}'
        temp_size = temp_size \
            if len(temp_size) < self._width \
            else temp_size[:self._width - 6] + '...'
        self._stdscr.addstr(
            self._amount_lines + 4, 1,
            temp_size + ' ' * (self._width - len(temp_size) - 2) + '|')

        temp_cwd = f'CWD{" " * (3 + self._padding_left_len - 3)}| ' \
                   f'{os.getcwd()}'
        temp_cwd = temp_cwd \
            if len(temp_cwd) < self._width \
            else temp_cwd[:self._width - 6] + '...'
        self._stdscr.addstr(
            self._amount_lines + 5, 1,
            temp_cwd + ' ' * (self._width - len(temp_cwd) - 2) + '|')

        self._stdscr.addstr(
            self._amount_lines + 6, 0,
            '-' * (3 + self._padding_left_len + 1) + '+' +
            '-' * (3 * self._amount_bytes_in_line + 1))

        self._stdscr.scrollok(False)
        try:
            self._stdscr.addch(self._height - 1, self._width - 1, '+')
        except curses.error:
            pass

    def __show_exception(self, exception):
        self._stdscr.addstr(
            2, 3 + self._padding_left_len + 3,
            'Exception!', curses.color_pair(1))
        message = str(exception)

        _length = self._amount_bytes_in_line * 3 - 1 - 13
        if len(message) <= _length:
            self._stdscr.addstr(
                3, 3 + self._padding_left_len + 3,
                f'Information: {message}', curses.color_pair(1))
        else:
            _length2 = self._amount_bytes_in_line * 3 - 3
            message_parsed = message.split()
            index = 0
            while index != len(message_parsed) - 1:
                if type(message_parsed[index]) != list:
                    message_parsed[index] = \
                        [len(message_parsed[index]), message_parsed[index]]
                if message_parsed[index][0] + 1 + \
                        len(message_parsed[index + 1]) < _length2:
                    message_parsed[index][0] += \
                        len(message_parsed[index + 1]) + 1
                    message_parsed[index].append(message_parsed.pop(index + 1))
                else:
                    index += 1

            self._stdscr.addstr(
                3, 3 + self._padding_left_len + 3,
                f'Information:',
                curses.color_pair(1))
            for i, arr in enumerate(message_parsed):
                self._stdscr.addstr(
                    4 + i, 3 + self._padding_left_len + 3,
                    f'   {" ".join(message_parsed[i][1:])}',
                    curses.color_pair(1))

    def __read(self, start_position, amount) -> bytes:
        self._file.seek(start_position)
        return self._file.read(amount)

    @staticmethod
    def __format(num, encoding='ascii', char_mode=False):
        if not char_mode:
            result = hex(num)[2:]
            if len(result) == 2:
                return result
            else:
                return f'0{result}'
        else:
            if 32 <= num <= 127:
                return f' {str(chr(num).encode(encoding=encoding))[2]}'
            else:
                return ' .'

    @staticmethod
    def __format_size(size):
        if size < 2 ** 10:
            return f'{size} b'
        elif size < 2 ** 20:
            return f'{round(size / 2 ** 10, 3)} Kb'
        elif size < 2 ** 30:
            return f'{round(size / 2 ** 20, 3)} Mb'
        elif size < 2 ** 40:
            return f'{round(size / 2 ** 30, 3)} Gb'
        elif size < 2 ** 50:
            return f'{round(size / 2 ** 40, 3)} Tb'
        else:
            return f'{round(size / 2 ** 50, 3)} bc'
