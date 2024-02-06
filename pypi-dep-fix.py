#!/usr/bin/env python3

import argparse
import ast
import os
import re


def setup_parser():
    """Create commandline argument parser."""
    parser = argparse.ArgumentParser()

    parser.add_argument("targetdir", default="", nargs=1,
                        help="Target source directory")

    parser.add_argument("modules", default="", nargs='+',
                        help="Name(s) of the module(s) to remove version requirements on")

    return parser


def run_search(patterns, line):
    """Test if the line matches any patterns."""
    for module, pattern in patterns.items():
        match = pattern.search(line)
        if match:
            return module, match
    return None, None


def make_patterns(modules):
    """Create regex patterns for each module."""
    patterns = {}
    for module in modules:
        patterns[module] = re.compile(f"^(Requires-Dist:)?[ ]*{module}[ ]*[[(!~=><]")
    return patterns


def find_files(path, patterns):
    """Find potential files to modify dependencies on."""
    dep_files = []
    file_whitelist = set(['requires.txt', 'requirements.txt', 'setup.cfg',
                          'setup.py', 'METADATA', 'PKG-INFO'])
    for root, _, files in os.walk(path):
        for name in files:
            filepath = os.path.join(root, name)
            if os.path.islink(filepath):
                continue
            if name not in file_whitelist:
                continue
            with open(filepath, 'r', encoding='utf-8',
                      errors='replace') as rfile:
                for line in rfile.readlines():
                    match, _ = run_search(patterns, line)
                    if match:
                        dep_files.append(filepath)
                        break
    return dep_files


def is_install_target(node):
    """Detect node is an assignment with the right target."""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            # not supporting tuple assignment at least yet
            if isinstance(target, ast.Name) and target.id == 'install_requires':
                return True
    return False


class ReplaceLocation():
    """Wrapper class for a location of a replacement target."""
    def __init__(self, line, start, end, module):
        self.line = line
        self.start = start
        self.end = end
        self.module = module

    def __str__(self):
        return f"line: {self.line}, start: {self.start}, end: {self.end}, module: {self.module}"


def find_locations(node, patterns):
    """Find replacement location target(s) to be updated."""
    locations = []
    if isinstance(node.value, ast.List):
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant):
                module, _ = run_search(patterns, elt.value)
                if module:
                    locations.append(ReplaceLocation(elt.end_lineno, elt.col_offset,
                                                     elt.end_col_offset, module))
    return locations


def code_replace(path, patterns):
    """Parse python to update a dependency."""
    contents = ''
    with open(path, encoding='utf-8', errors='replace') as pfile:
        contents = pfile.read()
    tree = ast.parse(contents)
    locations = []
    for node in ast.walk(tree):
        if is_install_target(node):
            locations += find_locations(node, patterns)
    new_contents = contents.splitlines()
    for location in locations:
        line = new_contents[location.line-1]
        new_line = f"{line[:location.start]}'{location.module}'{line[location.end:]}"
        new_contents[location.line-1] = new_line
    with open(path, 'w', encoding='utf-8') as pfile:
        pfile.writelines('\n'.join(new_contents))
        if contents.endswith('\n'):
            pfile.write('\n')


def text_replace(path, patterns):
    """Parse text to update a dependency."""
    new_contents = []
    # A bit dirty to do replace here but these are unlikely to be
    # important strings to program correctness.
    with open(path, 'r', encoding='utf-8', errors='replace') as pfile:
        contents = pfile.readlines()
        for line in contents:
            module, _ = run_search(patterns, line)
            if module:
                # text file with expected format
                # ::whitespace::module_name::whitespace::version_info
                # only remove everything after module_name
                name_start = line.find(module)
                new_line = line[:name_start+len(module)]
                if line.endswith('\n'):
                    new_line += '\n'
            else:
                new_line = line
            new_contents.append(new_line)
    with open(path, 'w', encoding='utf-8') as pfile:
        pfile.writelines(new_contents)


def update_dependencies(paths, patterns):
    """Remove the version dependencies for the given packages."""
    python_files = set(['setup.py'])
    for path in paths:
        if os.path.basename(path) in python_files:
            code_replace(path, patterns)
        else:
            text_replace(path, patterns)


def main():
    """Entry point function."""
    parser = setup_parser()
    args = parser.parse_args()

    patterns = make_patterns(args.modules)
    paths = find_files(args.targetdir[0], patterns)
    update_dependencies(paths, patterns)


if __name__ == '__main__':
    main()
