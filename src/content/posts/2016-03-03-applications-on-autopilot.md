---
canonical: https://www.joyent.com/blog/applications-on-autopilot
categories:
- Joyent, Docker
date: 2016-03-03T00:00:00Z
title: Implementing the autopilot pattern
tweet: Run your applications on autopilot
slug: applications-on-autopilot
---

Deploying containerized applications and connecting them together is a challenge because it forces developers to design for operationalization. Autopiloting applications are a powerful design pattern to solving these problems. By pushing the responsibility for understanding startup, shutdown, scaling, and recovery from failure into the application, we can build intelligent architectures that minimize human intervention in operation. But we can't rewrite all our applications at once, so we need a way to build application containers that can knit together legacy and greenfield applications alike. This project demonstrates the autopilot pattern by applying it to a simple microservices deployment using Nginx and two Node.js applications.

*[Check out the full article on the official Joyent blog...](https://www.joyent.com/blog/applications-on-autopilot)*
