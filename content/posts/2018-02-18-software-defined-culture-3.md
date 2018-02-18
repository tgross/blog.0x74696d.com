---
categories:
- talks
- culture
date: 2018-02-18T03:00:00Z
title: Software Defined Culture, Part 3 - Observability
slug: software-defined-culture-3-observability
---

This five-part series of posts covers a talk titled _Software Defined Culture_ that I gave at [DevOps Days Philadelphia 2016](https://www.devopsdays.org/events/2016-philadelphia/program/tim-gross/), [GOTO Chicago 2017](https://gotochgo.com/2017/sessions/43), and [Velocity San Jose 2017](https://vimeo.com/228067673).

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture](../software-defined-culture)
1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. [Part 2: Build for Operability](../software-defined-culture-2-operability)
3. Part 3: Build for Observability
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)

---

# Building for Observability

> "We have built mind-bogglingly complicated systems that we cannot see, allowing glaring performance problems to hide in broad daylight in our systems."

Bryan Cantrill, CTO of Joyent, said this back in 2006 in [ACM Queue](http://queue.acm.org/detail.cfm?id=1117401). And that was more than ten years ago! Turns out we were all building distributed systems back then, but now we've all embraced that we're building distributed systems, and these systems make the situation even harder.

In a distributed system, the gnarliest and most difficult problems to solve will only appear in production. This means we need to be able to understand what's happening in our production systems. They need to be observable, and the tools we use to obtain that observability must above all be _safe_ to use in production.

But that's not all. In his [_Open Letter to Monitoring/Alerting Companies_](https://www.kitchensoap.com/2015/05/01/openlettertomonitoringproducts/), John Allspaw says:

> "[T]ake as a first design principle that outages and other "untoward" events are handled not by a lone engineer, but more often than not by a team of engineers all with their different expertise and focus of attention."

That is, the tools that we're building should be collaborative. Don't simply create dashboards showing the metrics associated with your previous outage. Select tools that allow you to debug _in situ_ like DTrace and eBPF, and let you write code that can be committed and shared as part of the learning process. Select tools like [Honeycomb](https://honeycomb.io/), that allow you to iteratively build queries of events emitted by your system, which you can then share as playbooks for your next incident.

### Observability as a First-Class Requirement.

I once had responsibility for a Windows Distributed File System Replication (DFSR) cluster. In case you're not familiar, this is block storage distributed over the WAN (what could _possibly_ go wrong?). This was many years ago before I'd won my production battle scars, so when we selected the system we didn't really take into consideration how we could observe its operation. When our users started reporting bizarre file locking behavior (_gasp who could've thought!?_), we realized that DFSR had no way to tell us what it was doing. The best we could get out of it was a report that said "here's how much bandwidth I've saving in compression," which was not very helpful. We went through the 5 Stages of Observability Grief:

- Denial: "We don't really need to worry about monitoring this, right?"
- Anger: "Why can't we monitor this?!"
- Bargaining: "Microsoft, surely you have a tool to observe this... can we have yours?"
- Depression: "I've been on the phone for 2 months with Microsoft... will this never end?"
- "Fuck this, we'll build our own tools!"

I built our own monitoring tooling based on Window Management Instrumentation (WMI), which for a small engineering firm (rails and runways, not software) with a two person tech team was bit of a lift. This project ended up driving me to greater participation in Philadelphia Python Users Group (PhillyPUG), giving talks on debugging Python, and eventually my first serious ops role at DramaFever.

What does this charming origin story have to do with culture? Because we didn't have a strong culture of observability as a first-class requirement, we ended up burning a lot of time and energy in building our own tooling. Taking ownership of our observability empowered us to make better technical decisions in the future. It's also a cautionary tale for culture; if you're an organization that has a hard time in taking ownership of its own tooling, you may lose team members to organizations that don't.


### Debugability

The decisions you can make to improve observability take place at every level of the stack, from deployment platform choices all the way down to build flags.

If you're stripping your production binaries or passing `--fomit-frame-pointer` to your compiler, you're making tradeoffs around your ability to easily observe what's happening in your applications. To take a real-world example from Joyent, it's the difference between having a flame graph that says "well the problem is somewhere here in third-party code" and a flame graph that says "here's the exact part of the algorithm that's causing the slowdown, and we can improve the performance by switching from RSA to ECDSA."

![Flame graph without frame pointers](/images/20180218/flamegraph-no-framepointers.png)

![Flame graph with frame pointers](/images/20180218/flamegraph-with-framepointers.png)

If you're looking at those flame graphs and saying "no one in my organization even knows how to do that", you should probably hire someone who does. And if you're looking to "level up" your development skills as an intermediate developer, you would be well-served by learning how to profile at this level.

### Platform Choices

If you deploy onto a platform where you don't have root and can't even do something like start a debugger, run `perf`, or generate a flame graph? Well, I'm not telling you that you should never use Google App Engine or Heroku or Elastic Beanstalk, but you should definitely understand what you're giving up.

This extends to the choice of programming language as well. If your [language documentation](https://golang.org/doc/gdb) tells developers that debugging isn't a priority, what does this say about the culture of debugging?

> "GDB does not understand Go programs well... it is not a reliable debugger for Go programs, particularly heavily concurrent ones. Moreover, it is not a priority for the Go project to address these issues, which are difficult."

In the case of golang, third parties have stepped up and (somewhat) improved the situation, but most of the stdlib profiling tools have been intermittently broken on non-Linux platforms for years (you can see an example in my [_Be Careful What You Benchmark_](https://blog.0x74696d.com/posts/be-careful-what-you-benchmark/) post).

This isn't an intractable situation. If you think a language has a lot of other things going for it, you can invest in building better observability tooling for it. Joyent has famously done so with Node.js, and as they are adopting more golang, one of the first projects they've embarked on is improving their ability to debug golang software.

[![DTrace PID provider FBT for Go (with arguments) on SmartOS! In the second run we match on an arg value, stop, take a core dump and resume.](/images/20180218/dtrace-tweet.png)](https://twitter.com/jen20/status/853943464131780608)

![DTrace golang](/images/20180218/dtrace-golang.png)

### Culture of Observability

Simply having access to good tooling for observability doesn't get you much in the way of culture change. You have to use that tooling! If you only make a point of using your ability to observe your system when things are going very wrong, you won't have built up the skills to use them well. Moreover, as Charity Majors points out in [_Building Badass Engineers and Badass Teams_](https://honeycomb.io/blog/2016/10/part-5/5-building-badass-engineers-and-badass-teams/):

> Get used to interacting with your observability tooling every day. As part of your release cycle, or just out of curiosity. Honestly, things are broken all the time - you don’t even know what normal looks like unless you’re also interacting with your observability tooling under "normal" circumstances.

Making decisions that keep observability as a first class citizen aren't just important from a technical standpoint. The concept of observability applies to every aspect of an organization's operation. Being able to understand the impact of our behaviors is the only way to keep ourselves honest. This applies to everything from deploying software, to marketing campaigns, to making HR policy changes. Observability is the first requirement to becoming a [learning organization](https://www.youtube.com/watch?v=IdZaFzuOPUQ).

---

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture](../software-defined-culture)
1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. [Part 2: Build for Operability](../software-defined-culture-2-operability)
3. Part 3: Build for Observability
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)
