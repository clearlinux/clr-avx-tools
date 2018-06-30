#!/usr/bin/python3
import subprocess
import sys
import re
import argparse
import os

# MMX and SSE2 instructions
sse_instructions_xmm = set([
    "paddb", "paddd", "paddsb", "paddsw", "paddusb", "psubw",
    "paddusw", "paddw", "pmaddwd", "pmulhw", "pmullw", "psubb", "psubsb",
    "psubsw", "psubusb", "paddusw", "paddw", "pmaddwd", "pmulhw", "pmullw",
    "psubb", "psubd", "psubd", "psubsb", "psubsw", "psubusb", "psubusw"
])

# 0.1 value instructions
avx2_instructions_lv = set(["shrx", "rorx", "shlx", "shrx", "shrx", "movbe"])
avx2_instructions_ymm = set([
    "vpaddq", "vpaddd", "vpsubq", "vpsubd", "vmulpd", "vaddpd", "vsubpd",
    "vmulps", "vaddps", "vsubps", "vpmaxsq", "vpminsq", "vpmuludq",
    "vpand", "vpmaxud", "vpminud", "vpmaxsd", "vpmaxsw", "vpminsd",
    "vpminsw", "vpand", "vpor", "vpmulld"
])
avx512_instructions_lv = set()

# 1.0 value instructions
avx2_instructions = set([
    "vfmadd132ss", "vfmadd213ss", "vfmadd231ss", "vfmadd132sd",
    "vfmadd231sd", "vfmadd213sd",
    "vfmsub132ss", "vfmsub213ss", "vfmsub231ss", "vfmsub132sd", "vfmsub231sd",
    "vfmsub213sd",
    "vfnmadd132ss", "vfnmadd213ss", "vfnmadd231ss", "vfnmadd132sd",
    "vfnmadd231sd", "vfnmadd213sd",
    "vfnmsub132ss", "vfnmsub213ss", "vfnmsub231ss", "vfnmsub132sd",
    "vfnmsub231sd", "vfnmsub213sd",
])
avx512_instructions = set()

# 2.0 value instructions
avx2_instructions_hv = set([
    "vpclmulhqlqdq", "vpclmullqhqdq",
    "vfmadd132ps", "vfmadd213ps", "vfmadd231ps", "vfmadd132pd", "vfmadd231pd",
    "vfmadd213pd", "vfmsub132ps", "vfmsub213ps", "vfmsub231ps", "vfmsub132pd",
    "vfmsub231pd", "vfmsub213pd",
    "vfnmadd132ps", "vfnmadd213ps", "vfnmadd231ps", "vfnmadd132pd",
    "vfnmadd231pd", "vfnmadd213pd", "vfnmsub132ps", "vfnmsub213ps",
    "vfnmsub231ps", "vfnmsub132pd", "vfnmsub231pd", "vfnmsub213pd", "vdivpd",
])
avx512_instructions_hv = set()


sse_functions = dict()
avx2_functions = dict()
avx512_functions = dict()
sse_functions_ratio = dict()
avx2_functions_ratio = dict()
avx512_functions_ratio = dict()


verbose: int = 0
quiet: int = 0




def is_sse(instruction:str, args:str) -> float:

    val: float = -1.0
    if "xmm" in args:
        if ("pd" in instruction or "ps" in instruction or instruction in sse_instructions_xmm):
            val = 1.0
        else:
            val = 0.01
    return val


def is_avx2(instruction:str, args:str) -> float:
    val: float = -1.0

    if "ymm" in args:
        if ("pd" in instruction or "ps" in instruction or instruction in avx2_instructions_ymm) and "xor" not in instruction and "vmov" not in instruction:
            val = 1.0
        else:
            val = 0.01

    if instruction in avx2_instructions_lv:
        val = max(val, 0.1)
    if instruction in avx2_instructions:
        val = max(val, 1.0)
    if instruction in avx2_instructions_hv:
        val = max(val, 2.0)

    return val

def has_high_register(args: str) -> bool:
    return args.endswith((
        'mm16', 'mm17', 'mm18', 'mm19', 'mm20', 'mm21', 'mm22',
        'mm23', 'mm24', 'mm25', 'mm26', 'mm27', 'mm28', 'mm29',
        'mm30', 'mm31'
    ))

def is_avx512(instruction:str, args:str) -> float:
    val: float = -1.0

    if instruction in avx512_instructions_lv:
        val = max(val, 0.1)
    if instruction in avx512_instructions:
        val = max(val, 1.0)
    if instruction in avx512_instructions_hv:
        val = max(val, 2.0)

    if "xor" not in instruction and "ymm" in args and has_high_register(args):
        val = max(val, 0.02)
    if "xor" not in instruction and has_high_register(args):
        val = max(val, 0.01)

    if "zmm" in args:
        if ("pd" in instruction or "ps" in instruction or "vpadd" in instruction or "vpsub" in instruction or instruction in avx2_instructions_ymm) and "xor" not in instruction and "vmov" not in instruction:
            val = max(val, 1.0)
        else:
            val = max(val, 0.01)
        if is_avx2(instruction, args) > 0:
            val = max(val, is_avx2(instruction, args))


    return val


def print_top_functions() -> None:
    def ratio(f: float) -> str:
        f = f * 100
        f = round(f)/100.0
        return str(f)


    def summarize(table: dict, is_pct: bool, max_funcs: int = 5) -> None:
        for f in sorted(table, key=table.get, reverse=True)[:max_funcs]:
            f = "    %-30s\t%s" % (f, ratio(table[f]))

            if is_pct:
                print(f, "%s")
            else:
                print(f)

    sets = (
        ("SSE", sse_functions, sse_functions_ratio),
        ("AVX2", avx2_functions, avx2_functions_ratio),
        ("AVX512", avx512_functions, avx512_functions_ratio),
    )

    for set_name, funcs, funcs_ratio in sets:
        print("Top %s functions by instruction count" % set_name)
        summarize(funcs_ratio, True)
        print()

        print("Top %s functions by value" % set_name)
        summarize(funcs, False)
        print()


def do_file(filename: str) -> None:
    global verbose
    global quiet

    global total_sse_count
    global total_avx2_count
    global total_avx512_count

    global total_sse_score
    global total_avx2_score
    global total_avx512_score

    if quiet == 0:
        print("Analyzing", filename)

    function = ""

    sse_count = 0
    avx2_count = 0
    avx512_count = 0

    sse_score = 0.0
    avx2_score = 0.0
    avx512_score = 0.0

    instructions = 0

    total_sse_count = 0
    total_avx2_count = 0
    total_avx512_count = 0

    total_sse_score = 0.0
    total_avx2_score = 0.0
    total_avx512_score = 0.0


    out, err = subprocess.Popen(["objdump","-d", filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    alllines = out.decode("latin-1")
    lines =  alllines.split("\n")

    for line in lines:
        score_sse = -1.0
        score_avx2 = -1.0
        score_avx512 = -1.0

        sse_str = " "
        avx2_str = " "
        avx512_str = ""

        match = re.search("^(.*)\#.*", line)
        if match:
            line = match.group(1)
        
        match = re.search(".*[0-9a-f]+\:\t[0-9a-f\ ]+\t([a-zA-Z0-9]+) (.*)", line)

        if match:
            ins = match.group(1)
            arg = match.group(2)

            score_sse = is_sse(ins, arg)
            score_avx2 = is_avx2(ins, arg)
            score_avx512 = is_avx512(ins, arg)

            avx2_str= " "
            instructions += 1

        match = re.search("\<([a-zA-Z0-9_@\.\-]+)\>\:", line)
        if match:
            funcname = match.group(1)
            if instructions > 0 and verbose > 0:
                print(function,"\t",ratio(sse_count/instructions),"\t", ratio(avx2_count / instructions), "\t", ratio(avx512_count/instructions), "\t", avx2_score,"\t", avx512_score)

            if sse_count >= 1:
                sse_functions[function] = sse_score
                sse_functions_ratio[function] = 100.0 * sse_count / instructions
            if avx2_count >= 1:
                avx2_functions[function] = avx2_score
                avx2_functions_ratio[function] = 100.0 * avx2_count / instructions
            if avx512_count >= 1:
                avx512_functions[function] = avx512_score
                avx512_functions_ratio[function] = 100.0 * avx512_count/instructions

            total_sse_count += sse_count
            total_sse_score += sse_score

            total_avx2_count += avx2_count
            total_avx2_score += avx2_score

            total_avx512_count += avx512_count
            total_avx512_score += avx512_score

            instructions = 0
            function = funcname


            sse_count = 0
            avx2_count = 0
            avx512_count = 0

            sse_score = 0.0
            avx2_score = 0.0
            avx512_score = 0.0

        if score_sse >= 0.0:
            sse_str = str(score_sse)
            sse_score += score_sse
            sse_count += 1

        if score_avx2 >= 0.0:
            avx2_str = str(score_avx2)
            avx2_score += score_avx2
            avx2_count += 1

        if score_avx512 >= 0.0:
            avx512_str = str(score_avx512)
            avx512_score += score_avx512
            avx512_count += 1


        if verbose > 0:
            print(sse_str,"\t",avx2_str,"\t", avx512_str,"\t", line)
    if quiet <= 0:
        print_top_functions()
        print()
        print("File total (SSE): ", total_sse_count,"instructions with score", round(total_sse_score))
        print("File total (AVX2): ", total_avx2_count,"instructions with score", round(total_avx2_score))
        print("File total (AVX512): ", total_avx512_count,"instructions with score", round(total_avx512_score))
        print()
    return 0


def main():
    global verbose
    global quiet
    global total_avx2_count
    global total_avx512_count
    global total_avx2_score
    global total_avx512_score
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-q", "--quiet", help="decrease output verbosity", action="store_true")
    parser.add_argument("-1", "--unlinksse", help="unlink the file if it has no SSE instructions", action="store_true")
    parser.add_argument("-2", "--unlinkavx2", help="unlink the file if it has no AVX2 instructions", action="store_true")
    parser.add_argument("-5", "--unlinkavx512", help="unlink the file if it has no AVX512 instructions", action="store_true")
    parser.add_argument("filename", help = "The filename to inspect")

    args = parser.parse_args()
    if args.verbose:
        verbose = 1

    if args.quiet:
        verbose = 0
        quiet = 1

    do_file(args.filename)

    if args.unlinksse:
        if total_sse_count < 10 and total_sse_score <= 1.0:
            print(args.filename, "\tsse count:", total_sse_count,"\tsse value:", ratio(total_sse_score))
            try:
                os.unlink(args.filename)
            except:
                None

    if args.unlinkavx2:
        if total_avx2_count < 10 and total_avx2_score <= 5.0:
            print(args.filename, "\tavx2 count:", total_avx2_count,"\tavx2 value:", ratio(total_avx2_score))
            try:
                os.unlink(args.filename)
            except:
                None

    if args.unlinkavx512:
        if total_avx512_count < 20 and total_avx512_score < 10.0:
            print(args.filename, "\tavx512 count:", total_avx512_count,"\tavx512 value:", ratio(total_avx512_score))
            try:
                os.unlink(args.filename)
            except:
                None



if __name__ == '__main__':
    main()

