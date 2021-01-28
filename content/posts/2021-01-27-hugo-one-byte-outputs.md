---
categories:
- development
- meta
date: 2021-01-27T12:00:00Z
title: Hugo 1-byte outputs
slug: hugo-one-byte-outputs
---

A particularly annoying bug in Hugo that I've been running into is
that it will output 1-byte files for the index and other pages. This
is not sparking joy.

What's particularly bad about it is that it's not at all
consistent. Any given build will just randomly decide that the front
page or the RSS feed should be empty. So every time I pushed to
Netlify it'd be a crap shoot as to whether or not the whole site would
break. While I try to figure this out I've been building locally,
checking manually with `find -size 1c`, and then pushing the whole
build output directory to Netlify.

This is a good example of where a tool has made so much of their
stated value proposition about performance that they seem to have
forgotten to do the job correctly. It's the MongoDB of static website
generator software. And it's totally undebuggable of course; they give
you no tools except for ones that help you debug rendering performance
(which, I am forced to admit, are [pretty
nice](https://github.com/devopsdays/devopsdays-theme/issues/643)). I
probably have some small template bug that's only triggering some
interleaved concurrent rendering path in Hugo when the moon is waxing
full, resulting in a file that contains only a single newline.

Of course I dug through their GitHub issues looking for anything
similar and their answers always start with asking you to upgrade to
the very latest version. Which would be fine except that every single
time I've updated Hugo they've broken backwards compatibility in their
templates. If I wanted that kind of pain I would just fix the damn bug
myself. And hey it's open source so isn't that the beauty of it? But
it's a static website renderer with acute featuritis, which is exactly
the sort of nerd snipe that's going to find me writing my own from
scratch. As one does.
