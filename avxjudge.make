# -* makefile -*-
MAKEFILE := $(lastword $(MAKEFILE_LIST))
MAKEFILEDIR := $(dir $(MAKEFILE))

.SUFFIXES:	# Remove implicit rules
.PHONY: force
force:

# Don't try to update this makefile
$(MAKEFILE):
	:

# For all other files, run avxjudge.py
/%: force
	python3 $(MAKEFILEDIR)/avxjudge.py $(ARGS) $@
