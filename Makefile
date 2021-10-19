prefix = $(DESTDIR)/usr
bindir = $(prefix)/bin
bin_PROGRAMS = \
	clr-avx2-move.pl \
	clr-python-avx2 \
	clr-python-avx512 \
	elf-move.py \
	pypi-dep-fix.py

datadir = $(prefix)/share/clr-avx-tools
data_FILES = \
	avxjudge.py \
	avxjudge.make

all:

install:
	install -d $(bindir) $(datadir)
	install -m 755 -t $(bindir) $(bin_PROGRAMS)
	install -m 644 -t $(datadir) $(data_FILES)
