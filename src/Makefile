[B]MAKEFLAGS += --warn-undefined-variables
.DEFAULT_GOAL := build
SHELL = /bin/bash

PHONY:	*

clean:
	find .. -not -path "*/.git"   -not -path "*/src" -not -path "*/.git/*" -not -path "*/src/*" -not -path ".." -delete

serve:
	source $(VIRTUALENVWRAPPER_HOOK_DIR)/blog/bin/activate; hugo serve

build:
	source $(VIRTUALENVWRAPPER_HOOK_DIR)/blog/bin/activate; hugo
