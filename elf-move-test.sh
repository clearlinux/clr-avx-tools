#!/bin/bash

set -eEu -o pipefail

BUILDDIR2=$(mktemp -d)
BUILDDIR512=$(mktemp -d)
OUTDIR2=$(mktemp -d)
OUTDIR512=$(mktemp -d)
FMFILE2=$(mktemp)
FMFILE512=$(mktemp)

function cleanup() {
    rm -fr "${BUILDDIR2}" "${BUILDDIR512}" "${OUTDIR2}" "${OUTDIR512}" "${FMFILE2}" "${FMFILE512}"
}
trap 'cleanup' EXIT

function test_run() {
    local avx=$1
    eval local bdir='$BUILDDIR'$avx
    eval local odir='$OUTDIR'$avx
    eval local fmfile='$FMFILE'$avx
    local bindir="${bdir}/usr/bin"
    local libdir="${bdir}/usr/lib64"
    local othdir="${libdir}/other"
    local execdir="${bdir}/libexec"
    local testdir="${execdir}/installed-tests"
    local obindir="${odir}/usr/bin"
    local olibdir="${odir}/usr/lib64"
    local oothdir="${olibdir}/other"
    local oexecdir="${odir}/libexec"
    local otestdir="${oexecdir}/installed-tests"
    local obhash="${odir}/usr/share/clear/optimized-elf/binf318aeea7ee8fa18ccd1134488fa2b52a7da1027e8653282e777efb9f26bf087"
    local okhash="${odir}/usr/share/clear/optimized-elf/bin1f3d63a95df6b59ab4db9c074b158405094d9095e2d2fa0bcc17564065974b16"
    local oohash="${odir}/usr/share/clear/optimized-elf/other2edc7c466cbccbf89212468f6c54f0785ba4e8c70149bfdaa0f88caa1787164c"
    local oehash="${odir}/usr/share/clear/optimized-elf/exec99d1a87f7a980cc68ad95a08631e0e37e2150c47ceacaafd0447e93ccffb025c"
    local othash="${odir}/usr/share/clear/optimized-elf/testsd7746001d2b00ac33928146b7b98f4ec0fab1fc314e5813746b6cbe6184c931a"
    if [ $avx -eq 2 ]; then
        local hwcap="${odir}/usr/lib64/glibc-hwcaps/x86-64-v3/"
        local bhash="${odir}/usr/share/clear/optimized-elf/bin1a427c8d716b1eaec9c303348694c2155b9ddf9325d5e4d27de247f177745aba"
        local khash="${odir}/usr/share/clear/optimized-elf/bin3284524d4262e33b9c3e5bbc0cfbe186800edda33ad4ad6be39df8141f643e4b"
        local ohash="${odir}/usr/share/clear/optimized-elf/other1b24faa34f9c7fa000b814302ece384c03caacfd0a6d4d069f464f23d271f6d6"
        local ehash="${odir}/usr/share/clear/optimized-elf/exec52d6c5962d62ed9f53edddd75154b6de4217c73762727227af41d942185a90fc"
        local thash="${odir}/usr/share/clear/optimized-elf/testsbf720cc6e903b8ccf86e842d0430fd32970bc41bde3b610ee3148ca1d492eb98"
    else
        local hwcap="${odir}/usr/lib64/glibc-hwcaps/x86-64-v4/"
        local bhash="${odir}/usr/share/clear/optimized-elf/bin1bd9116225c23aa175719148f3a751b542db4863c2cc724f6f67ef98dc059687"
        local khash="${odir}/usr/share/clear/optimized-elf/bin949fbfae7b4a6afeaf4e937cd5f1bf8eb7e3cb10d9fd31cd3479282b66e1280e"
        local ohash="${odir}/usr/share/clear/optimized-elf/other20c15a5338517856cfd04365f00a0e37906e29b5cbd9ee1c7880de77024610d6"
        local ehash="${odir}/usr/share/clear/optimized-elf/execeaf539fc86c73ade19ccc6a610935357698630bf74d9df65b33d9c77d8823793"
        local thash="${odir}/usr/share/clear/optimized-elf/testse3b059ef79177facb34abe4331e9beb55718ac48d538970824a5e85b5eea6b26"
    fi

    mkdir -p "${othdir}"
    mkdir -p "${bindir}"
    mkdir -p "${testdir}"
    mkdir -p "${oothdir}"
    mkdir -p "${obindir}"
    mkdir -p "${otestdir}"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/bfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/setuid-file"
    chmod u+s "${bindir}/setuid-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/skip-file"
    echo -n -e \\x00 > "${bindir}/keep-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff > "${libdir}/lfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff > "${othdir}/ofile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff > "${execdir}/efile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff\\xff > "${testdir}/tfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\x00 > "${obindir}/bfile"
    echo -n -e \\x00 > "${obindir}/keep-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\x00\\x00 > "${olibdir}/lfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\x00\\x00\\x00 > "${oothdir}/ofile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\x00\\x00\\x00\\x00 > "${oexecdir}/efile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\x00\\x00\\x00\\x00\\x00 > "${otestdir}/tfile"

    python3 elf-move.py "avx${avx}" "${bdir}" "${odir}" "${fmfile}" --skip-path /usr/bin/skip-file --path /usr/bin/keep-file &> /dev/null
    diff "${fmfile}" "elf-move-test-fm${avx}" &> /dev/null
    [ -f "${hwcap}/lfile" ]
    [ -f "${bhash}" ]
    [ -f "${khash}" ]
    [ -f "${ohash}" ]
    [ -f "${ehash}" ]
    [ -f "${thash}" ]
    [ -f "${obhash}" ]
    [ -f "${okhash}" ]
    [ -f "${oohash}" ]
    [ -f "${oehash}" ]
    [ -f "${othash}" ]
}

test_run 2
test_run 512
