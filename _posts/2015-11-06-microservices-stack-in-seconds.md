---
layout: post
title: microservices-stack-in-seconds
category: Joyent, Docker
---

Over the last couple weeks I've been working on a project at Joyent to demonstrate the components of a container-native microservices architecture. Today I've put the pieces together. I'm using [Containerbuddy](https://github.com/joyent/containerbuddy) in a stack that includes Nginx, Couchbase, a Node.js application, Cloudflare DNS, and our Triton platform. All the components can be swapped out for your favorite ones just by changing a `docker-compose.yml` description.

And there's not a scheduler in sight! When you ditch your VMs and deploy on bare metal in an environment where containers have their own NIC(s), you don't need all that extra overhead. Simple tools will do the job for you.

*[Check out the full article on the official Joyent blog...](https://www.joyent.com/blog/how-to-dockerize-a-complete-application)*
