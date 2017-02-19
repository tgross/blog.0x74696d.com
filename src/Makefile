[B]MAKEFLAGS += --warn-undefined-variables
.DEFAULT_GOAL := build

PHONY:	*

clean:
	find .. -not -path "*/.git"   -not -path "*/src" -not -path "*/.git/*" -not -path "*/src/*" -not -path ".." -delete

serve:
	hugo serve

build:
	hugo
