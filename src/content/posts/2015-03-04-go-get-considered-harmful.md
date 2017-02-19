---
categories:
- golang
date: 2015-03-04T00:00:00Z
title: go get considered harmful
slug: go-get-considered-harmful
---

One of my favorite essays on Python packaging is Armin Ronacher's [Python Packaging: Hate, hate, hate everywhere](http://lucumr.pocoo.org/2012/6/22/hate-hate-hate-everywhere/). And one of the reasons why I thought of it lately is to remind me that Go isn't the only language with crazy dependency management problems.

# Friends don't let friends go get

Let's get the big one out of the way. The giant miss that Go made with dependencies was `go get`. Oh, it's cool and all the first time you use it, and then you realize that there's no pinning of versions. Open source projects that use `go get` to draw their dependencies from other libraries have no choice but to track the tip of each and every one of their dependencies (i.e. the HEAD of master on a typical Github project).

# Imports are not URLs

What makes this worse is that Gophers who have drunk the coolaid seem to have the impression that imports are supposed to be URLs. On planet Academia all URLs point to canonically versioned resources that never change, become unavailable, swap out the dependent paths for a proxy service for Github (more on this later), or have backwards incompatible changes pushed without a version bump.

When we step back and realize this, we also realize that the axiom that the Go language developers seem to have about "everything you need to know is in the code" is false. If we discard that axiom (and really, who cares? Are you not commiting your makefiles to the repo?), then more sane solutions present themselves.

# Cross-package imports

Heavens forbid if you want to use your own organization's fork of an open source project without going in and editing all their cross-package imports. This was particularly annoying for us for `goamz` because `github.com/crowdmob/goamz/dyanmo` would import `github.com/crowdmob/goamz/aws`, so you couldn't just update your own imports. And then when crowdmob gets bought by AdRoll and moves their repos, you aren't just updating a pointer somewhere in your build script, but instead you've got to chase down all the imports and all *their* imports. (I'm not picking on crowdmob or AdRoll here at all, by the way; they're as pinned in by this as everyone else.)

# Dependencies are more than imports

`go get` fetches dependencies, and their dependencies, and so on. But it doesn't help you to figure out what you've got. You can't do the equivalent of a `pip list`. Why is this important? Because after you've done `go get`, you now have to go through the licenses of every dependency you have and find out whether it's suitable for your organization.

><aside>Addendum: I need to head off a frequent objection that there's `go list`. It's not even close. It doesn't give you a list of the packages and their versions in the build environment.</aside>


# Convention doesn't isolate workspaces.

Picture this -- you're a brand new Go developer. Let's get started and check out the docs on how to set up your workspace:

> To get started, create a workspace directory and set GOPATH accordingly. Your workspace can be located wherever you like, but we'll use $HOME/go in this document. Note that this must not be the same path as your Go installation.

~~~
$ mkdir $HOME/go
$ export GOPATH=$HOME/go
~~~

Bam, we already gave a budding Go developer bad advice. Because he or she is off to the races with `go get` and is now polluting a shared namespace with dependency code that can't be version-pinned. You can't get away with having a shared `GOPATH`; this is probably obvious to some people but it's definitely not obvious to many of the developers I've encountered.

# Bad dependency management leads to bad workarounds

This sad story has led to a bunch of different workarounds, all of which are flawed in pretty serious ways.

## gopkg.in

The folks at [gopkg.in](http://labix.org/gopkg.in) have what is admittedly a pretty clever solution to this. You take out all your Github URLS and replace it with theirs, and they'll proxy to your Github repo to a specific tag. Except that it doesn't work with private repositories. And we've added another external point of failure to our builds.

## "Vendoring" / Godeps

This is the practice (of which Godeps is a variant) of sticking all your dependencies in your source code repo and committing them. Which means that upstream changes need to be individually downloaded to each source repo. Godeps at least gives you a way to list your packages, which is a start.

But you don't want every upstream commit in your repo's commit history, so this is typically done by just blowing away the commit history. Or you end up with git submodules, which are brittle as hell.

And if there are bugs in the upstream, now you have to re-vendor that package for every case you use it across all your repos, instead of just bumping a version number somewhere and testing.

# A totally unsexy but sane and correct approach

I suspect most of the problems could have been prevented or mitigated if the import syntax permitted version pinning. But barring the release of Go 2.0, here's what I've been doing. As far as I can tell this is the only way to do this that doesn't have horrible ways of breaking all the time.

The solution is this:

1.  You fork each dependency to its own repo that you control. This is every dependency and their dependencies. Don't edit them in any way (unless you have other patches, of course).
2.  You have a `.godeps/` directory at the root of your repo. It is ignored by `git` (or whatever you're using for source control).
3.  Your GOPATH is set to the root of your repo.
4.  You have a makefile in your project repo. It contains the target `get`. For each dependency that you're going to import, you have a line in the form `git clone git@mygit.example.com:MyOrg/somepackage .godeps/SomeThirdParty/somepackage && cd .godeps/SomeThirdParty/somepackage && git checkout <pinned version>`.


This results in a directory that looks like this:

~~~
    tgross@durandal:~/src/tgross/mygoproject$ tree -a
    |_ .git/
    |_ .gitignore
    |_ .godeps/
    |  |_ github.com/
    |     |_ ThirdPartyA/
    |     |  |_ somepackage/
    |     |_ ThirdPartyB
    |        |_ some-other-package
    |_ Dockerfile
    |_ Makefile
    |_ bin/
    |_ build/
    |_ doc/
    |_ src/
       |_ mylibrary/

~~~

And a makefile that might look like this:

~~~ make
MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail
.DEFAULT_GOAL := all

export GOPATH := $(shell pwd)/.godeps:$(shell pwd)
DEPS := .godeps/src/github.com

.PHONY:	*

all:	clean .godeps test build

clean:
	rm -rf .godeps/*
	rm -rf build/*

.godeps:
	mkdir -p .godeps
	git clone git@github.com:MyOrg/somepackage.git \
        ${DEPS}/ThirdPartyA/somepackage \
        && cd ${DEPS}/ThirdPartyA/somepackage && git checkout c7d7a7c
	git clone git@github.com:MyOrg/some-other-package.git \
        ${DEPS}/ThirdPartyB/some-other-package \
        && cd ${DEPS}/ThirdPartyB/some-other-package && git checkout aa3257c

test:
	go vet mylibrary
	go test mylibrary -v -race -coverprofile=coverage.out

build:
	docker build -t="my-container-image" .
~~~

Note that there's no re-writing imports here. Your Go code is blissfully unaware of the behind-the-scenes work you're doing here to give it the correctly pinned dependencies.

The advantages to this approach are:

1.  All deps can be pinned but pulled from private repos.
2.  No extra copies of deps to get stale, weird, etc.
3.  Each working environment is isolated.
4.  Easy to pick up and move to your CI environment.
5.  All deps have to be explicitly known, recursively.


# It's been a while

I haven't posted in a long while, so if you've followed this blog previously you might be happy (or angry, whichever) to know that I'm planning on spending a bit more time on this. So stay tuned for new posts in the coming weeks.
