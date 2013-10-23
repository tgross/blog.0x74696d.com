---
layout: post
title: "AUFS is AUFul"
category: ops
---

Ok, so I'm being admittedly silly with this post's title. I've been working a good bit lately on a deployment orchestration system that's relying on Docker, which in turn relies on the unioning file system AUFS. And what's come out of that for me is that for a lot of deployments Docker is the wrong tool for the job. The guys at dotCloud have done a great job at rapidly creating a community around Docker, but -- and this shouldn't surprise anyone -- the Docker model supports their particular business model much more than it does the kinds of deployment's I'm working with. And a very large piece of this discrepency comes from the limitations of AUFS.
