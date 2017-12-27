[B]MAKEFLAGS += --warn-undefined-variables
.DEFAULT_GOAL := build
SHELL = /bin/bash

.PHONY:	*

clean:
	find . -path './build/*' -delete

serve:
	source $(VIRTUALENVWRAPPER_HOOK_DIR)/blog/bin/activate; hugo serve

build:
	source $(VIRTUALENVWRAPPER_HOOK_DIR)/blog/bin/activate; hugo

setup:
	@( \
		source /usr/local/bin/virtualenvwrapper.sh; \
		lsvirtualenv -b | grep '^blog$$' || (mkvirtualenv blog && pip install pygments); \
	)
