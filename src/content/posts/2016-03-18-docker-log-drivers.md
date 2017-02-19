---
canonical: https://www.joyent.com/blog/docker-log-drivers
categories:
- Joyent, Docker
date: 2016-03-18T00:00:00Z
title: Production Docker logs on Triton
slug: docker-log-drivers
---

In a [previous post](/posts/docker-logging) I talked about an approach I took getting logs out of Docker containers when I first started using Docker way back at the end of 2013. But Docker has done a lot of growing up since then!

Using `docker logs` to get our container logs works in development but in production we need to centralize our logs. Triton has support for the syslog, Graylog, and Fluentd log drivers and we can use them to support production-ready log collection.

*[Check out the full article on the official Joyent blog...](https://www.joyent.com/blog/docker-log-drivers)*
