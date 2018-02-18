---
categories:
- talks
- culture
date: 2018-02-18T00:00:00Z
title: Software Defined Culture, Part 0
slug: software-defined-culture
---

This five-part series of posts covers a talk titled _Software Defined Culture_ that I gave at [DevOps Days Philadelphia 2016](https://www.devopsdays.org/events/2016-philadelphia/program/tim-gross/), [GOTO Chicago 2017](https://gotochgo.com/2017/sessions/43), and [Velocity San Jose 2017](https://vimeo.com/228067673). I think the talk got better and each time I iterated on it. The talk was full of dumb jokes and silly gifs, whereas these posts will remove the visual gags and maybe elaborate on a few points that got rushed-through or that I've had some thoughts on since.

First, a warning. These posts will get a bit ranty. I'm talking about culture and the decisions we make around technical choices. But we have to be careful talking about culture. It's easy (especially as technologists) to be incredibly tone deaf when talking about culture. It's easy to make assumptions that your experiences are the same as other people's experiences. So for these posts, keep in mind that they're based on my experiences working mostly in small and mid-size organizations, working with enterprise developers in customer organizations, and being part of the technical communities I've been a part of personally. Your mileage may vary.

Second, some disclaimers. I'm going to quote a few people in these posts, but none of these people would necessarily endorse any particular position I'm making here. I'm also going to poke some fun at various technologies. These are all technologies I've personally worked with. So if I'm not making fun of your favorite technology, it's not because it's necessarily any good but just that I haven't worked with it before.

If you'd like to skip ahead to the rest of the series:

1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. [Part 2: Build for Operability](../software-defined-culture-2-operability)
3. [Part 3: Build for Observability](../software-defined-culture-3-observability)
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)


## Shipping the Org Chart

My friend and former colleague Bridget Kromhout is fond of saying ["containers won't fix your broken culture"](https://queue.acm.org/detail.cfm?id=3185224). And she's right. Ryn Daniels, one of the authors of _Effective DevOps_, said in their [keynote at Velocity NY 2016](https://www.oreilly.com/ideas/building-bridges-with-devops-velocity-ny-2016) that "tools won't fix your broken culture." And they're right.

This is the essence of the problem we face as technologists trying to improve our organizations. We have an embarrassment of technical tooling and best practices, but none of it really fixes our human problems. Hell, most of the time it barely fixes our technical problems.

I live in Philadelphia, and like many communities we have a Slack, and there's a devops channel. And every few months it seems we get an exchange like this:

![Slack channel](/images/20180218/slack-devops.png)

And, sure, maybe this response could be a little more constructive. But the point is that many people are confusing the tooling for the model of working. Using "devops tools" by themselves doesn't mean you're going to make the cultural changes we need to make to succeed. Often tooling is treated like a kind of a spiritual bypass -- "I'm using Docker, so I'm doing The DevOps".

Well the reason this doesn't work is because of something called _Conway's Law_, which was coined by Melvin Conway in his 1967 paper _How Do Committees Invent?_

> "Any organization that designs a system (defined more broadly here than just information systems) will inevitably produce a design whose structure is a copy of the organization's communication structure."

It's important to keep in mind here that "system" doesn't just mean the technical system it also means the cultural system. Human beings are the biggest distributed system. Or as Andrew Clay Shafer likes to say, organizations are a "socio-technical system."

## Chaotic Feedback

But like all complex systems, cultural systems are subject to chaotic feedback mechanisms. Subtle disturbances in equilibrium can build up to have large effects. Could we use these mechanisms to make technical choices to improve our culture?

Instinctively we all know that making bad technical choices can influence our culture. We know that if we don't build for reliability, the operations team will hate the development team. We know that if don't build for self-serviceability, the development teams will hate the operations team. We know that we don't build for flexibility, the production management team will frustrated with the inability of the development team to react quickly to changing market conditions.

If you were up all night every night over the weekend because PagerDuty was sending alerts over some crap deployments, then on Monday the team is going to be tired and maybe cranky at each other. In an org where there's a separate operations team, the operators trust will be eroded every time they get paged unnecessarily. That erosion of trust is a technical decision influencing your culture.

Last April, Bill Higgins at IBM had a [great blog post](https://medium.com/@BillHiggins/tools-as-a-catalyst-for-culture-change-f012b2c0b527) where he was talking about bringing new tools to a project team to catalyze a change in the way the team organized. He uses the words "magic" a lot.

> "The magic is in the new, better practices that the tools enable. A tool is a vehicle for practices. Practices directly shape habits and tacit assumptions. Habits and tacit assumptions are the foundations of culture."

The idea what he keeps coming back to the all these tools had amazing surface usability but the magic was actually about the new methods and collaboration that they generated. GitHub is "just a pretty web UI on git", right? But what it enables is a workflow around peer review, collaborative software development, and communal ownership of code. Slack is "just a pretty web UI on IRC", right? But unlike IRC, you can get non-technical people to use it. Slack channels become a place where technical teams (and their bots!) and non-technical teams can share a common medium of communication.

Culture influences tools but we can clearly see that tools can influence culture as well. This back-and-forth was illustrated nicely by Avi Vig in an AMA on Reddit (of all places) about his experience as an operations engineer at Etsy:

> "A lot of CD is to do with culture, much more than tools... Once you have the culture moving in the right direction, where developers are happy pushing code and owning software problems, and operations teams are OK letting go of the control and working with developers, the tools become less important."

If we know our technical choices can influence our culture, how can we make technical choices that will reinforce the values that we want in our organizations? I've come up with four guidelines for technical decision making which I'm going to grandiosely call the "4 principles of software defined culture." The remaining posts in this series will hit on each of these:

1. [Part 1: Build for Reliability](../software-defined-culture-1-reliability)
2. [Part 2: Build for Operability](../software-defined-culture-2-operability)
3. [Part 3: Build for Observability](../software-defined-culture-3-observability)
4. [Part 4: Build for Responsibility](../software-defined-culture-4-responsibility)
