---
layout: post
title: Consul and etcd in the Autopilot Pattern
category: Joyent, Docker
canonical: https://www.joyent.com/blog/consul-etcd-on-triton
---

Applications developed with the Autopilot Pattern are self-operating and self-configuring but use an external service catalog like Consul or etcd to store and coordinate global state. ContainerPilot sends the service catalog heartbeats to record that an instance of an application is still up and running. Both Consul and etcd have interesting assumptions about their topology that end users deploying on Triton should be aware of.

*[Check out the full article on the official Joyent blog...](https://www.joyent.com/blog/consul-etcd-on-triton)*
