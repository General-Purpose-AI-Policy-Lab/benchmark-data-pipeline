"""CLI: `python -m benchmark_data {refresh,build,check,parity}`."""

import argparse
import logging
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="benchmark_data", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("refresh", help="download the feeds into 0_input/feed/ (network)")
    sub.add_parser("build", help="build 2_database/ from 0_input/feed/ (offline)")
    sub.add_parser("check", help="compare 2_database/ and 3_views/ with their expected copies")
    sub.add_parser("parity", help="compare 3_views/ with the consumers' frozen outputs (reports/)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(message)s", stream=sys.stdout)
    if args.command == "refresh":
        from benchmark_data.refresh import refresh
        refresh()
    elif args.command == "build":
        from benchmark_data.build import build
        build()
    elif args.command == "check":
        from benchmark_data.check import check
        return 0 if check() else 1
    elif args.command == "parity":
        from benchmark_data.parity import parity
        parity()
    return 0


if __name__ == "__main__":
    sys.exit(main())
