---
canonical: https://www.joyent.com/blog/containerpilot-telemetry
categories:
- Joyent
- Docker
date: 2016-04-12T00:00:00Z
title: Monitoring and scaling with ContainerPilot telemetry
slug: monitoring-and-scaling-with-application-telemetry
---

Application health checking is a key feature of ContainerPilot (formerly Containerbuddy). The user-defined health check gives us a binary way of determining whether the application is working. If the application is healthy, ContainerPilot sends a heartbeat to the discovery catalog, and if it's not, other ContainerPilot-enabled applications will stop sending requests to it. But automatic scaling of a service depends on more than just the pass/fail of a health check. Every application has key performance indicators that tell us if the service is nearing overload and should be scaled up or is under-utilized and can be scaled down.

*[Check out the full article on the official Joyent blog...](https://www.joyent.com/blog/containerpilot-telemetry)*
