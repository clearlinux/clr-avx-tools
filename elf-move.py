#!/usr/bin/env python3

import argparse
import itertools
import os
import sys
from collections import OrderedDict


def setup_parser():
    """Create commandline argument parser."""
    parser = argparse.ArgumentParser()

    parser.add_argument("btype", help="Binary type [avx2, avx512]")

    parser.add_argument("installdir", help="Content directory to scan")

    parser.add_argument("targetdir", help="Target directory for output")

    parser.add_argument("outfile", nargs='?', default="",
                        help="Deprecated: unused")

    parser.add_argument("-s", "--skip", action="store_true",
                        default=False,
                        help="Don't process elf binaries")

    parser.add_argument("-v", "--verbose", action="store_true",
                        default=False,
                        help="Add output for unused files in the installdir")

    parser.add_argument("-S", "--skip-path", default=[], nargs=1,
                        action="append",
                        help="Don't process files with the target path(s)")

    parser.add_argument("-p", "--path", default=[], nargs=1,
                        action="append",
                        help="Handle path regardless of file type (overrides skip)")

    return parser


def process_install(args):
    """Create output based on the installdir.

    Also output to stdout the non-elf file paths and hashes (useful to compare
    different build types).
    """
    always_process = set()
    for item in args.path:
        always_process.add(item[0])
    args.path = always_process
    filemap = OrderedDict()
    for root, _, files in os.walk(args.installdir):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                if os.stat(filepath).st_mode & os.path.stat.S_ISUID != 0:
                    continue
            except:
                continue
            data = bytearray(4096)
            memv = memoryview(data)
            virtpath = os.path.join('/',
                                    filepath.removeprefix(args.installdir))

            with open(filepath, 'rb', buffering=0) as ifile:
                ifile.readinto(memv)
                elf = memv[:4] == b'\x7fELF'
                if elf or virtpath in args.path:
                    filemap[virtpath] = [True,
                                         filepath]
                else:
                    filemap[virtpath] = [False,
                                         filepath]
    return filemap


def move_content(args, filemap):
    """Use the filemap to populate targetidr."""
    if len(filemap) == 0:
        return

    skips = set(itertools.chain.from_iterable(args.skip_path))

    if args.btype == 'avx2':
        optimized_prefix = 'V3'
    elif args.btype == 'avx512':
        optimized_prefix = 'V4'
    else:
        return
    optimized_dir = os.path.join(args.targetdir, optimized_prefix)
    os.makedirs(optimized_dir, exist_ok=True)
    for virtpath, val in filemap.items():
        elf = val[0]
        source = val[1]
        if virtpath in skips:
            if args.verbose:
                print(f"Skipping path {virtpath}")
            continue
        if elf:
            if args.skip and virtpath not in args.path:
                if args.verbose:
                    print(f"Skipping elf file {virtpath}")
                continue
            dest = os.path.join(optimized_dir, virtpath[1:])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if args.verbose:
                print(f"Installing {dest}")
            os.rename(source, dest)
        elif args.verbose:
            print(f"{virtpath} not installed")


def main():
    """Entry point function."""
    parser = setup_parser()
    args = parser.parse_args()
    if args.btype not in ("avx2", "avx512"):
        print(f"Error: btype '{args.btype}' not supported (needs to be either avx2 or avx512)")
        sys.exit(-1)
    if args.outfile:
        print('Warning: outfile argument is longer used, ignoring.')
    if args.targetdir.endswith('/usr/share/clear/optimized-elf/'):
        # Catch previous invocation with targetdir being the
        # optimized-elf directory that is no longer correct.
        print('Error: Full path for optimized-elf detected!')
        print(' targetdir should be the root of the output directory.')
        sys.exit(-1)

    filemap = process_install(args)

    move_content(args, filemap)


if __name__ == '__main__':
    main()
