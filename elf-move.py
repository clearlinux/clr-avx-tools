#!/usr/bin/env python3

import argparse
import hashlib
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

    parser.add_argument("outfile", help="Output file name")

    parser.add_argument("-s", "--skip", action="store_true",
                        default=False,
                        help="Don't process elf binaries")

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
            sha = hashlib.sha256()
            data = bytearray(4096)
            memv = memoryview(data)
            virtpath = os.path.join('/',
                                    filepath.removeprefix(args.installdir))

            # some files have the same contents so include the full path
            # in the hash
            sha.update(virtpath.encode())
            sha.update(args.btype.encode())
            elf = memv[:4] == b'\x7fELF'
            if elf or virtpath in args.path:
                filemap[virtpath] = [True,
                                     filepath,
                                     sha.hexdigest()]
            else:
                filemap[virtpath] = [False,
                                     filepath,
                                     sha.hexdigest()]
    return filemap


def copy_original(virtpath, targetdir, optimized_dir):
    sha = hashlib.sha256()
    filename = os.path.join(targetdir, virtpath[1:])
    sha.update(virtpath.encode())
    sha.update("SSE4.2".encode())
    shasum = sha.hexdigest()
    if "/usr/bin/" in filename:
        shasum = "bin" + shasum
    elif "/libexec/installed-tests" in filename:
        shasum = "tests" + shasum
    elif "/libexec/" in filename:
        shasum = "exec" + shasum
    elif os.path.dirname(filename).endswith("/usr/lib64"):
        return
    else:
        shasum = "other" + shasum
    try:
        os.link(filename, os.path.join(optimized_dir, shasum))
    except:
        pass


def write_outfile(args, filemap):
    """Use the filemap to populate targetidr."""
    if len(filemap) == 0:
        return

    skips = set(itertools.chain.from_iterable(args.skip_path))

    optimized_dir = os.path.join(args.targetdir,
                                 'usr/share/clear/optimized-elf/')
    hwcaps_dir = os.path.join(args.targetdir, 'usr/lib64/glibc-hwcaps')
    avx2_ldir = os.path.join(hwcaps_dir, 'x86-64-v3')
    avx512_ldir = os.path.join(hwcaps_dir, 'x86-64-v4')
    os.makedirs(optimized_dir, exist_ok=True)
    os.makedirs(avx2_ldir, exist_ok=True)
    os.makedirs(avx512_ldir, exist_ok=True)
    if os.path.basename(args.outfile) != args.outfile:
        os.makedirs(os.path.dirname(args.outfile), exist_ok=True)

    with open(args.outfile, 'a', encoding='utf-8') as ofile:
        for virtpath, val in filemap.items():
            elf = val[0]
            source = val[1]
            shasum = val[2]
            if virtpath in skips:
                continue
            # prefix files from /usr/bin with a bin prefix so autospec can put
            # them in the right subpackage
            if "/usr/bin/" in source:
                shasum = "bin" + shasum
            elif "/libexec/installed-tests" in source:
                shasum = "tests" + shasum
            elif "/libexec/" in source:
                shasum = "exec" + shasum
            elif os.path.dirname(source).endswith("/usr/lib64"):
                # Install /usr/lib64 content directly.
                # This is okay as the libs are only are used when the
                # required hardware exists.
                if args.btype == 'avx2':
                    os.rename(source,
                              os.path.join(avx2_ldir,
                                           os.path.basename(source)))
                elif args.btype == 'avx512':
                    os.rename(source,
                              os.path.join(avx512_ldir,
                                           os.path.basename(source)))
            else:
                shasum = "other" + shasum

            # /usr/lib64 content was installed already
            if elf and not os.path.dirname(source).endswith("/usr/lib64"):
                if args.skip and virtpath not in args.path:
                    continue
                copy_original(virtpath, args.targetdir, optimized_dir)
                ofile.write(f"{args.btype}\n")
                ofile.write(f"{virtpath}\n")
                ofile.write(f"{shasum}\n")
                os.rename(source, os.path.join(optimized_dir, shasum))
            else:
                print(f"{virtpath} {shasum}")

    # Don't leave around empty filemaps
    if os.path.getsize(args.outfile) == 0:
        os.remove(args.outfile)


def main():
    """Entry point function."""
    parser = setup_parser()
    args = parser.parse_args()
    if args.btype != "avx2" and args.btype != "avx512":
        print(f"Error: btype '{args.btype}' not supported (needs to be either avx2 or avx512)")
        sys.exit(-1)
    if args.targetdir.endswith('/usr/share/clear/optimized-elf/'):
        # Catch previous invocation with targetdir being the
        # optimized-elf directory that is no longer correct.
        print('Error: Full path for optimized-elf detected!')
        print(' targetdir should be the root of the output directory.')
        sys.exit(-1)

    filemap = process_install(args)

    write_outfile(args, filemap)


if __name__ == '__main__':
    main()
