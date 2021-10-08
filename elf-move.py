#!/usr/bin/env python3

import argparse
import hashlib
import os
from collections import OrderedDict


def setup_parser():
    """Create commandline argument parser."""
    parser = argparse.ArgumentParser()

    parser.add_argument("type", default="", nargs=1,
                        help="Binary type [avx, avx2, avx512]")

    parser.add_argument("installdir", default="", nargs=1,
                        help="Target directory from install")

    parser.add_argument("targetdir", default="", nargs=1,
                        help="Target directory from install")

    parser.add_argument("outfile", default="", nargs=1,
                        help="Output file name")

    parser.add_argument("-s", "--skip", action="store_true",
                        default=False,
                        help="Don't process manipulate elf binaries")

    return parser


def process_install(args):
    """Create output based on the installdir.

    Also output to stdout the non-elf file paths and hashes (useful to compare
    different build types).
    """
    filemap = OrderedDict()
    for root, _, files in os.walk(args.installdir[0]):
        for name in files:
            filepath = os.path.join(root, name)
            if os.path.islink(filepath):
                continue
            sha = hashlib.sha256()
            data = bytearray(4096)
            memv = memoryview(data)
            virtpath = os.path.join('/',
                                    filepath.removeprefix(args.installdir[0]))

            with open(filepath, 'rb', buffering=0) as ifile:
                blk = ifile.readinto(memv)
                elf = memv[:4] == b'\x7fELF'
                while blk := ifile.readinto(memv):
                    sha.update(memv[:blk])
                if elf:
                    filemap[virtpath] = [args.type[0],
                                         filepath,
                                         sha.hexdigest()]
                else:
                    filemap[virtpath] = [None,
                                         filepath,
                                         sha.hexdigest()]
    return filemap


def write_outfile(args, filemap):
    """Use the filemap to populate targetidr."""
    if len(filemap) == 0:
        return

    os.makedirs(args.targetdir[0], exist_ok=True)
    if os.path.basename(args.outfile[0]) != args.outfile[0]:
        os.makedirs(os.path.dirname(args.outfile[0]), exist_ok=True)

    with open(args.outfile[0], 'a', encoding='utf-8') as ofile:
        for virtpath, val in filemap.items():
            btype = val[0]
            source = val[1]
            shasum = val[2]
            # prefix files from /usr/bin with a bin prefix so autospec can put then in the right subpackage
            if "/usr/bin/" in source:
                shasum = "bin" + shasum
            if "/libexec/" in source:
                shasum = "libexec" + shasum
            if btype:
                if args.skip:
                    continue
                ofile.write(f"{btype}\n")
                ofile.write(f"{virtpath}\n")
                ofile.write(f"{shasum}\n")
                os.rename(source, os.path.join(args.targetdir[0], shasum))
            else:
                print(f"{virtpath} {shasum}")


def main():
    """Entry point function."""
    parser = setup_parser()
    args = parser.parse_args()

    filemap = process_install(args)

    write_outfile(args, filemap)


if __name__ == '__main__':
    main()
