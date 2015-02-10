MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail
.DEFAULT_GOAL := all

PHONY:	*

all:	serve

# build the Docker container
build-container:
	docker build -t="tgross.github.io" .

# create a new post w/ today's date
# make post TITLE="Some Post" --> _posts/2015-02-09-some-post.md
post:
	$(eval SLUG := $(shell echo -n '${TITLE}' | sed -e 's/[^[:alnum:]]/-/g' \
| tr -s '-' | tr A-Z a-z))
	$(eval FILE := '_posts/$(shell date "+%Y-%m-%d")-${SLUG}.md')
	echo --- > ${FILE}
	echo "layout: post" >> ${FILE}
	echo "title: ${TITLE}" >> ${FILE}
	echo --- >> ${FILE}

build:
	docker run --rm -it -w /src \
		-v ~/src/tgross/tgross.github.io:/src \
		tgross.github.io \
		bundle exec jekyll build

serve:
	docker run --rm -it -p 4000:4000 -w /src \
		-v ~/src/tgross/tgross.github.io:/src \
		tgross.github.io \
		bundle exec jekyll serve --watch --trace
