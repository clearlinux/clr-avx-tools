#!/usr/bin/perl
use strict;
if (scalar @ARGV < 2) {
    print "clr-avx2-move.pl <libsubdir> <pluginsuffix> [file listing]\n";
    print "Examples:\n";
    print "  clr-avx2-move.pl haswell .avx2 /usr/lib64/*.so*\n";
    print "  clr-avx2-move.pl haswell/avx512_1 .avx512 /usr/lib64/*.so*\n";
    exit 0;
}

my $libsubdir = shift @ARGV;
my $pluginsuffix = shift @ARGV;
my @files;
my %createddirs;

# Sort the incoming file listing
for my $f (@ARGV) {
    # Ignore if it's not a file
    next unless (-f $f);
    # Put symlinks at the beginning of the list
    # (to avoid breaking them when we move the actual file)
    if (-l $f) {
        unshift @files, $f;
    } else {
        push @files, $f;
    }
}

for my $f (@files) {
    # Run readelf -d on the file to get the SONAME
    open READELF, "-|", "readelf", "-d", $f;
    my @soname = grep / *0x\w+ \(SONAME\)\s/, <READELF>;
    close READELF;

    next if $? >> 8;  # not ELF, ignore (could be a linker script)

    my $to;
    if (scalar @soname) {
        # This ELF module has a SONAME, so it's a library:
        # Move it to the $libsubdir subdir
        $f =~ m,^(.*?)/?([^/]+)$,;
        my $dirname = "$1/$libsubdir";
        $to = "$dirname/$2";
        mkdir($dirname) unless defined($createddirs{$dirname});
        $createddirs{$dirname} = 1;
    } else {
        $to = $f . $pluginsuffix;
    }
    rename($f, $to) and print "$f -> $to\n"
        or print STDERR "rename(\"$f\", \"$to\"): $!\n";
}
