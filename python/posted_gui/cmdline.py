#!/usr/bin/env python3
import argparse

from posted_gui.launchPG import launchPG
from posted.units.units import convUnit


# main launch function
def main():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        # prog='posted.py',
        description='Potsdam open-source techno-economic database GUI',
        epilog='For further details, please consult the source code or code documentation.',
    )
    parser.add_argument('tid')

    # parse arguments
    args = parser.parse_args()

    launchPG(tid=args.tid)

    return


# __main__ routine
if __name__ == '__main__':
    main()
