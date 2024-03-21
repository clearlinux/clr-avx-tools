#!/usr/bin/python3

import subprocess
import sys
import copy

libprovides = dict()
librequires = dict()

matrix = dict()
visited = dict()


def add_provides(lib, function):
    global libprovides
    
    if not lib in libprovides.keys():
        libprovides[lib] = dict()
    libprovides[lib][function] = "Yes"
    
def add_requires(lib, function):
    global librequires
    
    if not lib in librequires.keys():
        librequires[lib] = dict()
    librequires[lib][function] = "Yes"
    
    
def add_from_to_func(req, prov, func):
    global matrix
    
    if not req in matrix.keys():
        matrix[req] = dict()
    if not prov in matrix[req].keys():
        matrix[req][prov] = list()
        
    matrix[req][prov].append(func)

def process_library(filename):
    
    pipeout = subprocess.check_output(['nm', '-D', filename]).decode("utf-8")
    
    lines = pipeout.split('\n')
    for line in lines:
        words = line.split()

        if len(words) > 1:        
            if words[0] == 'U':
                add_requires(filename, words[1])
            if words[1] == 'T':
                add_provides(filename, words[2])
            if words[1] == 'W':
                add_provides(filename, words[2])
    


def process_binary(filename):
    process_library(filename)
    pipeout = subprocess.check_output(['ldd', '-r', filename]).decode("utf-8").replace("\t","")
    lines = pipeout.split('\n')
    for line in lines:
        words = line.split()
        if len(words) > 2:
            process_library(words[2])


def create_matrix():
    for file in librequires.keys():
        for symbol in librequires[file].keys():
            for file2 in libprovides.keys():
                if file2 == '/usr/lib64/ld-linux-x86-64.so.2':
                    continue
                if file2 == '/usr/lib64/libc.so.6':
                    continue
                if file2 == '/usr/lib64/haswell/libc.so.6':
                    continue

                if file2 == '/usr/lib64/libpthread.so.0':
                    continue
                if file != file2 and symbol in libprovides[file2].keys():
                    add_from_to_func(file, file2, symbol)

def print_matrix(req, level):
    if not req in matrix.keys():
        return
        
    for prov in matrix[req].keys():
            start = ""
            for i in range(level):
                start += "\t"
            reason = "(" + str(len(matrix[req][prov])) + ") " + matrix[req][prov][0]
            if len(matrix[req][prov]) > 1:
                reason += " " +  matrix[req][prov][1]
            if len(matrix[req][prov]) > 2:
                reason += " " +  matrix[req][prov][2]
            if len(matrix[req][prov]) > 3:
                reason += " " +  matrix[req][prov][3]
            if len(matrix[req][prov]) > 4:
                reason += " " +  matrix[req][prov][4]
            if len(matrix[req][prov]) > 5:
                reason += " " +  matrix[req][prov][5]
            if len(matrix[req][prov]) > 5:
                reason += " ..."
            print(start, req, "pulls in", prov, "because of", reason)
            if prov in visited:
                continue
                
            visited[prov] = "Yes"
            print_matrix(prov, level + 1)

def main():
    process_binary(sys.argv[1])
    create_matrix()
    print_matrix(sys.argv[1], 0)

if __name__ == '__main__':
    main()
