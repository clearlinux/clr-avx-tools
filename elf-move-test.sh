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
    eval local outdir='$OUTDIR'$avx
    if [ $avx -eq 2 ]; then
        local outdirv="${outdir}/V3"
    else
        local outdirv="${outdir}/V4"
    fi
    eval local builddir='$BUILDDIR'$avx
    local bindir="${builddir}/usr/bin"
    local libdir="${builddir}/usr/lib64"
    local othdir="${libdir}/other"
    local execdir="${builddir}/libexec"
    local testdir="${execdir}/installed-tests"
    local oddothdir="${builddir}/usr/foo/usr/lib64"

    local obindir="${outdirv}/usr/bin"
    local olibdir="${outdirv}/usr/lib64"
    local oothdir="${olibdir}/other"
    local oexecdir="${outdirv}/libexec"
    local otestdir="${oexecdir}/installed-tests"
    local ooddothdir="${outdirv}/usr/foo/usr/lib64"

    mkdir -p "${othdir}"
    mkdir -p "${bindir}"
    mkdir -p "${testdir}"
    mkdir -p "${oddothdir}"
    mkdir -p "${oothdir}"
    mkdir -p "${obindir}"
    mkdir -p "${otestdir}"
    mkdir -p "${ooddothdir}"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/bfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/setuid-file"
    chmod u+s "${bindir}/setuid-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/skip-file"
    echo -n -e \\x00 > "${bindir}/keep-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff > "${libdir}/lfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff > "${othdir}/ofile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff > "${execdir}/efile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff\\xff > "${testdir}/tfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff\\xff\\xff > "${oddothdir}/oofile"

    python3 elf-move.py "avx${avx}" "${builddir}" "${outdir}" --skip-path /usr/bin/skip-file --path /usr/bin/keep-file &> /dev/null

    [ -f "${obindir}/bfile" ]
    [ ! -f "${obindir}/setuid-file" ]
    [ ! -f "${obindir}/skip-file" ]
    [ -f "${obindir}/keep-file" ]
    [ -f "${olibdir}/lfile" ]
    [ -f "${oothdir}/ofile" ]
    [ -f "${oexecdir}/efile" ]
    [ -f "${otestdir}/tfile" ]
    [ -f "${ooddothdir}/oofile" ]
}

test_run 2
test_run 512
