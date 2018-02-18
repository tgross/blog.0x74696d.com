---
categories:
- talks
- culture
date: 2018-02-18T02:00:00Z
title: Software Defined Culture, Part 2 - Operability
slug: software-defined-culture-2-operability
---

This five-part series of posts covers a talk titled _Software Defined Culture_ that I gave at [DevOps Days Philadelphia 2016](https://www.devopsdays.org/events/2016-philadelphia/program/tim-gross/), [GOTO Chicago 2017](https://gotochgo.com/2017/sessions/43), and [Velocity San Jose 2017](https://vimeo.com/228067673).

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture](../software-defined-culture)
1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. Part 2: Build for Operability
3. [Part 3: Build for Observability](../software-defined-culture-3-observability)
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)

---

# Building for Operability

For purposes of this section, I'm talking about operability as the ability for teams to deploy and operate their software well. Ideally this should be in some kind of self-service way, where developers don't need to go through some other team ("operators") to deploy software.

One of the notional frameworks that has popped up around this in the last few years is GIFFE ("Google Infrastructure for Everyone Else"). This notion has largely reified itself in the last year especially in Kubernetes and the hodge-podge of vaguely related projects under the banner of the Cloud Native Computing Foundation (CNCF).

But "Google does it this way, so should we" suggests that you have similar problems to Google. Spoiler alert: this is unlikely to be the case. I've talked with teams at some of the largest retailers in the world and discovered giant e-commerce properties fitting in the equivalent of a handful of racks. Your startup (and mine!) is a tiny fraction of the scale, so why would we expect the solutions to be the same?

Orchestrators like Kubernetes are designed to handle a wide diversity of organizational requirements, and this is reflected in a huge amount of choice (the diversity of networking plugins alone!) that becomes incumbent upon the operators to handle. Cindy Sridharan's [excellent blog post](https://medium.com/@copyconstruct/schedulers-kubernetes-and-nomad-b0f2e14a896
) from last summer dives into the choices her organization made around Kubernetes versus a less complex scheduler like Nomad.

### Who's Complexity?

Most engineers are familiar with the concept of essential vs incidental complexity, but perhaps less commonly understood is how the "essentialness" of complexity is deeply tied to ones perspective. _The complexity of Kubernetes is essential complexity from the perspective of Kubernetes-the-project, but it is incidental complexity from the perspective of your organization._

The problem doesn't quite end at the orchestration layer. There has been a strong trend over the last few years towards pushing "intelligence" out of the application and into infrastructure components. The narrative is that application developers shouldn't have to worry about concerns like service discovery, tracing, failover, configuration, etc. and that they should be solely focused on "business logic." I've been told 2018 is The Year of the Service Mesh, for example.

Whether this trend has been exacerbated by the large number of VC-backed infrastructure startups who have a vested interest in this being the prevailing narrative is left as an exercise for the reader. But in addition to reducing application developers to line-of-business specialists ready to be washed away in the next wave of Taylorist automation, this leads to some serious problems when it comes to running applications in production.

If the application behavior has been abstracted away from its environment, this means the application developer can't understand the real-world behavior of their application without running it on the platform either. It's a reincarnation of RPC by remote function call; the application developer can't really treat the infrastructure like an abstraction. The application developer can't really pretend that a database cluster is sitting at localhost when there are application-specific semantics to how it behaves when replication degrades. This just leads to "works on my machine" and we're back to the same problem we were trying to solve with all our new fancy orchestration tools in the first place!

### Self-Operating Applications

What's the alternative? While I was at Joyent I worked on a project called [ContainerPilot](https://github.com/joyent/containerpilot), along with design patterns that we collectively called the Autopilot Pattern. The concept of the Autopilot Pattern was that the application should be responsible for its own lifecycle as much as possible. Once deployed by a (minimal) orchestration platform, applications can find the service discovery database, gossip their configuration, elect leaders, and trigger events in their own lifecycle. ContainerPilot was envisioned as a container init system that would help bridge the gap to these behaviors for legacy applications. The Joyent folks have continued on with the project after my departure, but I've seen it at work successfully at large enterprise retailers and startups alike.

The [Habitat](https://www.habitat.sh/) project by Chef is another example of this same philosophy at work. Habitat goes a step further by owning the entire build process for the application container as well. By packaging the application and its automation together, you get consistent deployments, automated dependency awareness, and decentralized intelligence. But more importantly, you empower development teams to understand the production behavior of their applications.

Google infrastructure is probably awesome but does it solve a problem we actually have? "GIIPABDISAPWAH" is less catchy than "GIFEE", I'll admit. Building for operability, as described here, builds a culture of trust (there's that word again) between developers and operators, a culture of empowerment for your developers, and a culture with fewer silos.

---

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture](../software-defined-culture)
1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. Part 2: Build for Operability
3. [Part 3: Build for Observability](../software-defined-culture-3-observability)
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)
