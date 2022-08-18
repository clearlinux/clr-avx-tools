#!/usr/bin/env python3

import argparse
import hashlib
import itertools
import os
import sys
from collections import OrderedDict

btype = "SSE4.2"

def setup_parser():
    """Create commandline argument parser."""
    parser = argparse.ArgumentParser()

    parser.add_argument("type", default="", nargs=1,
                        help="Binary type [avx2, avx512]")

    parser.add_argument("installdir", default="", nargs=1,
                        help="Content directory to scan")

    parser.add_argument("targetdir", default="", nargs=1,
                        help="Target directory for output")

    parser.add_argument("outfile", default="", nargs=1,
                        help="Output file name")

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
    global btype
    """Create output based on the installdir.

    Also output to stdout the non-elf file paths and hashes (useful to compare
    different build types).
    """
    always_process = set()
    for item in args.path:
        always_process.add(item[0])
    args.path = always_process
    filemap = OrderedDict()
    for root, _, files in os.walk(args.installdir[0]):
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
                                    filepath.removeprefix(args.installdir[0]))

            with open(filepath, 'rb', buffering=0) as ifile:
                blk = ifile.readinto(memv)
                # some files have the same contents so include the full path
                # in the hash
                sha.update(virtpath.encode())
                sha.update(btype.encode())
                elf = memv[:4] == b'\x7fELF'
                if elf or virtpath in args.path:
                    filemap[virtpath] = [args.type[0],
                                         filepath,
                                         sha.hexdigest()]
                else:
                    filemap[virtpath] = [None,
                                         filepath,
                                         sha.hexdigest()]
    return filemap


def copy_original(virtpath, targetdir, optimized_dir):
    data = bytearray(4096)
    sha = hashlib.sha256()
    memv = memoryview(data)
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
        None


def write_outfile(args, filemap):
    global btype
    """Use the filemap to populate targetidr."""
    if len(filemap) == 0:
        return

    skips = set(itertools.chain.from_iterable(args.skip_path))

    optimized_dir = os.path.join(args.targetdir[0],
                                 'usr/share/clear/optimized-elf/')
    hwcaps_dir = os.path.join(args.targetdir[0], 'usr/lib64/glibc-hwcaps')
    avx2_ldir = os.path.join(hwcaps_dir, 'x86-64-v3')
    avx512_ldir = os.path.join(hwcaps_dir, 'x86-64-v4')
    os.makedirs(optimized_dir, exist_ok=True)
    os.makedirs(avx2_ldir, exist_ok=True)
    os.makedirs(avx512_ldir, exist_ok=True)
    if os.path.basename(args.outfile[0]) != args.outfile[0]:
        os.makedirs(os.path.dirname(args.outfile[0]), exist_ok=True)

    with open(args.outfile[0], 'a', encoding='utf-8') as ofile:
        for virtpath, val in filemap.items():
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
                if btype == 'avx2':
                    os.rename(source,
                              os.path.join(avx2_ldir,
                                           os.path.basename(source)))
                elif btype == 'avx512':
                    os.rename(source,
                              os.path.join(avx512_ldir,
                                           os.path.basename(source)))
            else:
                shasum = "other" + shasum

            # /usr/lib64 content was installed already
            if btype and not os.path.dirname(source).endswith("/usr/lib64"):
                if args.skip and virtpath not in args.path:
                    continue
                copy_original(virtpath, args.targetdir[0], optimized_dir)
                ofile.write(f"{btype}\n")
                ofile.write(f"{virtpath}\n")
                ofile.write(f"{shasum}\n")
                os.rename(source, os.path.join(optimized_dir, shasum))
            else:
                print(f"{virtpath} {shasum}")

    # Don't leave around empty filemaps
    if os.path.getsize(args.outfile[0]) == 0:
        os.remove(args.outfile[0])


def main():
    global btype;
    """Entry point function."""
    parser = setup_parser()
    args = parser.parse_args()
    btype = args.type[0];
    if args.targetdir[0].endswith('/usr/share/clear/optimized-elf/'):
        # Catch previous invocation with targetdir being the
        # optimized-elf directory that is no longer correct.
        print('Error: Full path for optimized-elf detected!')
        print(' targetdir should be the root of the output directory.')
        sys.exit(-1)

    filemap = process_install(args)

    write_outfile(args, filemap)


if __name__ == '__main__':
    main()
