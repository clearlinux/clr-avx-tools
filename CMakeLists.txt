project(clr-avx-tools)
cmake_minimum_required(VERSION 3.0)
install(PROGRAMS
        avxjudge.py
        clr-avx2-move.pl
        clr-python-avx2
        clr-python-avx512
        DESTINATION bin)
