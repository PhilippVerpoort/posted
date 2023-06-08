#!/usr/bin/env python3
import argparse

from posted.units.units import convUnit


# main execution function
def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='posted',
        description='Potsdam open-source techno-economic database',
        epilog='For further details, please consult the source code or code documentation.',
    )
    subparsers = parser.add_subparsers(title='commands', dest='command', help='sub-command help')

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
    if cmd == 'conv':
        convFactor = convUnit(args.fromUnit, args.toUnit, args.flow)
        print(f"{convFactor*args.value:.2f} {args.toUnit}")

    return


# __main__ routine
if __name__ == '__main__':
    main()
