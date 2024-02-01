#!/bin/bash

set -eEu -o pipefail

BUILDDIR2=$(mktemp -d)
BUILDDIR512=$(mktemp -d)
BUILDDIRA=$(mktemp -d)
OUTDIR2=$(mktemp -d)
OUTDIR512=$(mktemp -d)
OUTDIRA=$(mktemp -d)

function cleanup() {
    rm -fr "${BUILDDIR2}"
    rm -fr "${BUILDDIR512}"
    rm -fr "${BUILDDIRA}"
    rm -fr "${OUTDIR2}"
    rm -fr "${OUTDIR512}"
    rm -fr "${OUTDIRA}"
}
trap 'cleanup' EXIT

function test_run() {
    local avx=$1
    if [ $avx = 2 ]; then
        eval local outdir='$OUTDIR2'
        local outdirv="${outdir}/V3"
        local elfarg="avx2"
        eval local builddir='$BUILDDIR2'
    elif [ $avx = 512 ]; then
        eval local outdir='$OUTDIR512'
        local outdirv="${outdir}/V4"
        local elfarg="avx512"
        eval local builddir='$BUILDDIR512'
    else
        eval local outdir='$OUTDIRA'
        local outdirv="${outdir}/VA"
        local elfarg="apx"
        eval local builddir='$BUILDDIRA'
    fi
    local bindir="${builddir}/usr/bin"
    local sbindir="${builddir}/usr/sbin"
    local libdir="${builddir}/usr/lib64"
    local othdir="${libdir}/other"
    local execdir="${builddir}/libexec"
    local testdir="${execdir}/installed-tests"
    local oddothdir="${builddir}/usr/foo/usr/lib64"

    local obindir="${outdirv}/usr/bin"
    local osbindir="${outdirv}/usr/bin"
    local olibdir="${outdirv}/usr/lib64"
    local oothdir="${olibdir}/other"
    local oexecdir="${outdirv}/libexec"
    local otestdir="${oexecdir}/installed-tests"
    local ooddothdir="${outdirv}/usr/foo/usr/lib64"

    mkdir -p "${othdir}"
    mkdir -p "${bindir}"
    mkdir -p "${sbindir}"
    mkdir -p "${testdir}"
    mkdir -p "${oddothdir}"
    mkdir -p "${oothdir}"
    mkdir -p "${obindir}"
    mkdir -p "${otestdir}"
    mkdir -p "${ooddothdir}"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/bfile"
    ln -s "${bindir}/bfile" "${bindir}/lbfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/sbfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/setuid-file"
    chmod u+s "${bindir}/setuid-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff > "${bindir}/skip-file"
    echo -n -e \\x00 > "${bindir}/keep-file"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff > "${libdir}/lfile"
    ln -s "${libdir}/lfile" "${libdir}/llfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff > "${othdir}/ofile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff > "${execdir}/efile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff\\xff > "${testdir}/tfile"
    echo -n -e \\x7f\\x45\\x4c\\x46\\xff\\xff\\xff\\xff\\xff\\xff > "${oddothdir}/oofile"

    python3 elf-move.py "${elfarg}" "${builddir}" "${outdir}" --skip-path /usr/bin/skip-file --path /usr/bin/keep-file &> /dev/null

    [ -f "${obindir}/bfile" ]
    [ ! -f "${obindir}/lbfile" ]
    [ -f "${obindir}/sbfile" ]
    [ ! -f "${obindir}/setuid-file" ]
    [ ! -f "${obindir}/skip-file" ]
    [ -f "${obindir}/keep-file" ]
    [ -f "${olibdir}/lfile" ]
    [ ! -f "${olibdir}/llfile" ]
    [ -f "${oothdir}/ofile" ]
    [ -f "${oexecdir}/efile" ]
    [ -f "${otestdir}/tfile" ]
    [ -f "${ooddothdir}/oofile" ]
}

test_run 2
test_run 512
test_run a
