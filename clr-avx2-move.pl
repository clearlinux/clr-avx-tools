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
my %moves;
my %createddirs;

sub scandir($$) {
    my $dir = $_[0];
    my $lambda = $_[1];

    # Only recurse into this dir if it exists and is not a symlink
    return unless (-d $dir && ! -l $dir);

    opendir(my $dh, $dir) or die "Couldn't open $dir: $!";
    while (readdir $dh) {
        next if $_ eq "." || $_ eq "..";

        $lambda->("$dir/$_");
    }
    closedir $dh;
}

sub add_file($) {
    my $f = $_[0];
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

    return if $? >> 8;  # not ELF, ignore (could be a script)
    return unless $elftype eq "EXEC" || $elftype eq "DYN";

    my $to;
    if ($soname || $interpreter) {
        # This ELF file either has a SONAME (it's a library), an interpreter
        # (it's an executable), or both (it's an executable library).
        # Move it to the $libsubdir subdir.
        $f =~ m,^(.*?)/?([^/]+)$,;
        my $dirname = "$1/$libsubdir";
        $to = "$dirname/$2";

        my $ignored_error;
        make_path($dirname, { error => \$ignored_error })
            unless defined($createddirs{$dirname});
        $createddirs{$dirname} = 1;
    } else {
        # No SONAME or interpreter, it must be a plugin.
        $to = $f . $pluginsuffix;
    }
    $moves{$f} = $to;
}

# Save STDERR for us, but redirect it to /dev/null for readelf
open(REAL_STDERR, ">&STDERR");
open(STDERR, ">/dev/null");

# Make sure readelf outputs in English
$ENV{LC_ALL} = 'C';

# Build the file listing
my $binlambda = sub {
    # executables must be regular files and +x
    my $f = $_[0];
    add_file($f) if (-f $f && -x $f);
};
scandir("$root/bin", $binlambda);
scandir("$root/sbin", $binlambda);
scandir("$root/usr/bin", $binlambda);
scandir("$root/usr/sbin", $binlambda);
scandir("$root/usr/local/bin", $binlambda);
scandir("$root/usr/local/sbin", $binlambda);

my $liblambda;
$liblambda = sub {
    $_ = $_[0];
    if (-f $_) {
        # It's a library if it's named *.so, *.so.* (except *.so.avx*)
        add_file($_) if /\.so($|\.(?!avx))/;
    } elsif (-d $_) {
        # Lib dirs are recursive
        scandir($_, $liblambda) unless m,/$libsubdir$,;
    }
};
scandir("$root/usr/lib64", $liblambda);

# Automatically flush STDOUT
$| = 1;

while (my ($f, $to) = each %moves) {
    rename($f, $to) and print "$f -> $to\n"
        or print REAL_STDERR "rename(\"$f\", \"$to\"): $!\n";
}
