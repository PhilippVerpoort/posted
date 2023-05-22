#!/usr/bin/env python3
import argparse

from src.gui.launchPG import launchPG
from src.python.units.units import convUnit


# main launch function
def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        # prog='posted.py',
        description='Potsdam open-source techno-economic database',
        epilog='For further details, please consult the source code or code documentation.',
    )
    subparsers = parser.add_subparsers(title='commands', dest='command', help='sub-command help')

    # create the parser for the "gui" command
    parser_gui = subparsers.add_parser('gui')
    parser_gui.add_argument('tid')

    # create the parser for the "conv" command
    parser_conv = subparsers.add_parser('conv')
    parser_conv.add_argument('--flow')
    parser_conv.add_argument('value', type=float)
    parser_conv.add_argument('fromUnit')
    parser_conv.add_argument('toUnit')

    # parse arguments
    args = parser.parse_args()
    cmd = args.command

    # switch between different commands
    if cmd == 'gui':
        launchPG(tid=args.tid)
    elif cmd == 'conv':
        convFactor = convUnit(args.fromUnit, args.toUnit, args.flow)
        print(f"{convFactor*args.value:.2f} {args.toUnit}")

    return


# __main__ routine
if __name__ == '__main__':
    main()
