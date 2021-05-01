import os
import sys
import argparse

from user_interface.win import Window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Allow user to view files in hex mode.\n'
                    'To see help in program press `h`.')

    parser.add_argument('file', type=str,
                        help='the file to be opened in hex mode')
    parser.add_argument('-e', '--encoding', type=str,
                        default='ascii', nargs='?',
                        help='the encoding in which to read the file')
    parser.add_argument('-r', '--rainbow', action='store_true',
                        help='switches rainbow mode')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.file is None:
        print('There is no path to file in arguments!')
        sys.exit(1)
    if not os.path.exists(args.file):
        print(f'There is no such file: {os.path.abspath(args.file)}!')
        sys.exit(2)
    if not os.path.isfile(args.file):
        print(f'There is not a file: {os.path.abspath(args.file)}!')
        sys.exit(3)

    try:
        chr(30).encode(encoding=args.encoding)
    except LookupError:
        print(f'Incorrect encoding: {args.encoding}!')
        sys.exit(4)

    if os.path.getsize(args.file) == 0:
        print(f'File is emtpy!')
        sys.exit(0)

    try:
        open(args.file, mode='rb')
    except PermissionError:
        print(f'Permission denied: {args.file}!\n'
              f'Restart the program as a root.')
        sys.exit(5)

    win = Window(args.file, args.encoding, args.rainbow)
    win.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
