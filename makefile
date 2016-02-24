MAKEFLAGS += --warn-undefined-variables
.DEFAULT_GOAL := serve

PWD := $(shell pwd)

PHONY:	*

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

serve:
	docker run --rm -it -p 4000:4000 \
		-e POLLING=true \
		-v $(PWD):/srv/jekyll \
		jekyll/jekyll:pages
