#!/usr/bin/env python3
import argparse
from pathlib import Path

from posted.sources import dump_sources
from posted.units import unit_convert


# main execution function
def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='posted',
        description='Potsdam open-source techno-economic database',
        epilog='For further details, please consult the source code or code \
              documentation.',
    )
    subparsers = parser.add_subparsers(title='commands', dest='command',
                                       help='sub-command help')

    # create the parser for the "conv" command
    parser_conv = subparsers.add_parser('conv')
    parser_conv.add_argument('--flow')
    parser_conv.add_argument('value', type=float)
    parser_conv.add_argument('fromUnit')
    parser_conv.add_argument('toUnit')

    # create the parser for the "dump-sources" command
    parser_conv = subparsers.add_parser('dump-sources')
    parser_conv.add_argument('filePath', type=Path)

    # parse arguments
    args = parser.parse_args()
    cmd = args.command

    # switch between different commands
    if cmd == 'conv':
        conv_factor = unit_convert(args.fromUnit, args.toUnit, args.flow)
        print(f"{conv_factor*args.value:.2f} {args.toUnit}")
    elif cmd == 'dump-sources':
        dump_sources(args.filePath)

    return


# __main__ routine
if __name__ == '__main__':
    main()
