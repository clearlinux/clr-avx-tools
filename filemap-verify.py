#!/usr/bin/env python3

import argparse
import hashlib
import os
import sys


def get_full_map(fmdir):
    full_map = {}
    for fmfile in os.listdir(fmdir):
        if not fmfile.startswith('filemap-'):
            print(f"Skipping {fmfile}")
            continue
        with open(os.path.join(fmdir, fmfile), encoding='utf8') as mfile:
            iter_mfile = iter(mfile.readlines())
            for line in iter_mfile:
                btype = line
                opath = next(iter_mfile)
                fhash = next(iter_mfile)
                full_map[fhash.strip()] = (btype.strip(), opath.strip())
    return full_map


def get_hash_map(path):
    hash_map = {}
    for root, dirs, files in os.walk(path):
        for fname in files:
            try:
                with open(os.path.join(root, fname), 'rb') as ifile:
                    sha = hashlib.sha256()
                    sha.update(ifile.read())
                    hash_map[sha.hexdigest()] = os.path.join(root, fname)
            except Exception:
                pass
    return hash_map


def find_match(path, hash_map):
    sha = hashlib.sha256()
    with open(path, 'rb') as ifile:
        sha.update(ifile.read())
    if sha in hash_map and hash_map[sha] != path:
        return hash_map[sha]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fmdir', '-f', default='/usr/share/clear/filemap/', help='The filemap directory')
    parser.add_argument('--match_base', '-m', default='/usr/', help='The base directory of os content')
    parser.add_argument('--oedir', '-o', default='/usr/share/clear/optimized-elf/', help='The optimized elf directory')
    parser.add_argument('--quiet', '-q', action='store_true', default=False, help='Do not print results')
    args = parser.parse_args()

    full_map = get_full_map(args.fmdir)
    match_list = []

    for root, _, files in os.walk(args.oedir):
        for oefile in files:
            if oefile in full_map and not args.quiet:
                print(f"{oefile} -> {full_map[oefile][1]}:{full_map[oefile][0]}")
            else:
                match_list.append((root, oefile))

    if match_list:
        if not args.quiet:
            for _, oefile in match_list:
                print(f"Error: {oefile} not in filemap", file=sys.stderr)
        sys.exit(-1)


if __name__ == '__main__':
    main()
