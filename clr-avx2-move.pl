#!/usr/bin/perl
use strict;
use File::Path qw(make_path);

if (scalar @ARGV < 3) {
    print "clr-avx2-move.pl <libsubdir> <pluginsuffix> <buildroot>\n";
    print "Examples:\n";
    print "  clr-avx2-move.pl haswell .avx2 /var/tmp/buildroot\n";
    print "  clr-avx2-move.pl haswell/avx512_1 .avx512 /var/tmp/buildroot\n";
    exit 0;
}

my $libsubdir = shift @ARGV;
my $pluginsuffix = shift @ARGV;
my $root = shift @ARGV;
my @files;
my %createddirs;

sub scandir($$$) {
    my $dir = $_[0];
    my $needs_exec = $_[1];
    my $name_match = $_[2];

    # Only recurse into this dir if it exists and is not a symlink
    return unless (-d $dir && ! -l $dir);

    opendir(my $dh, $dir) or die "Couldn't open $dir: $!";
    while (readdir $dh) {
        next if $_ eq "." || $_ eq "..";

        my $f = "$dir/$_";
        if (-f $f) {
            next unless (-x $f || !$needs_exec);
            next unless m/$name_match/;

            # Put symlinks at the beginning of the list
            # (to avoid breaking them when we move the actual file)
            if (-l $f) {
                unshift @files, $f;
            } else {
                push @files, $f;
            }
        } elsif (-d $f) {
            scandir($f);
        }
    }
    closedir $dh;
}

# Build the file listing
scandir("$root/bin", 1, qr//);
scandir("$root/sbin", 1, qr//);
scandir("$root/usr/bin", 1, qr//);
scandir("$root/usr/sbin", 1, qr//);
scandir("$root/usr/local/bin", 1, qr//);
scandir("$root/usr/local/sbin", 1, qr//);
scandir("$root/usr/lib64", 0, qr/\.so\.?/);

# Save STDERR for us, but redirect it to /dev/null for readelf
open(REAL_STDERR, ">&STDERR");
open(STDERR, ">/dev/null");

# Automatically flush STDOUT
$| = 1;

# Make sure readelf outputs in English
$ENV{LC_ALL} = 'C';

for my $f (@files) {
    my $soname = 0;
    my $interpreter = 0;
    my $elftype;

    # Run readelf -hdl on the file to get the SONAME and INTERP
    open READELF, "-|", "readelf", "-hdl", $f;
    while (<READELF>) {
        $elftype = $1 if /^\s*Type:\s*(\w+)\b/;
        $soname = 1 if / *0x\w+ \(SONAME\)\s/;
        $interpreter = 1 if /^\s*INTERP\s/;
    }
    close READELF;

    next if $? >> 8;  # not ELF, ignore (could be a script)
    next unless $elftype eq "EXEC" || $elftype eq "DYN";

    my $to;
    if ($soname || $interpreter) {
        # This ELF file either has a SONAME (it's a library), an interpreter
        # (it's an executable), or both (it's an executable library).
        # Move it to the $libsubdir subdir.
        $f =~ m,^(.*?)/?([^/]+)$,;
        my $dirname = "$1/$libsubdir";
        $to = "$dirname/$2";
        make_path($dirname) unless defined($createddirs{$dirname});
        $createddirs{$dirname} = 1;
    } else {
        # No SONAME or interpreter, it must be a plugin.
        $to = $f . $pluginsuffix;
    }
    rename($f, $to) and print "$f -> $to\n"
        or print REAL_STDERR "rename(\"$f\", \"$to\"): $!\n";
}
