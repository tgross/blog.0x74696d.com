---
categories:
- talks
- culture
date: 2018-02-18T01:00:00Z
title: Software Defined Culture, Part 1 - Reliability
slug: software-defined-culture-1-reliability
---

This five-part series of posts covers a talk titled _Software Defined Culture_ that I gave at [DevOps Days Philadelphia 2016](https://www.devopsdays.org/events/2016-philadelphia/program/tim-gross/), [GOTO Chicago 2017](https://gotochgo.com/2017/sessions/43), and [Velocity San Jose 2017](https://vimeo.com/228067673).

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture]({{< ref "2018-02-18-software-defined-culture-0.md" >}})
1. Part 1: Build for Reliability
2. [Part 2: Build for Operability]({{< ref "2018-02-18-software-defined-culture-2.md" >}})
3. [Part 3: Build for Observability]({{< ref "2018-02-18-software-defined-culture-3.md" >}})
4. [Part 4: Build for Responsibility]({{< ref "2018-02-18-software-defined-culture-4.md" >}})

---

# Building for Reliability

Failure to build for reliability means we develop a culture of firefighting. Firefighting becomes a rut for organizations. Things are broken, we rush out fixes, and we pile on technical debt. The "temporary" hacks lead to problems that come back, grow, and cascade. Urgency starts to supercede importance. That is, the thing that needs to be fixed _right now_ sets back the mission of the organization as a whole. Problems become crises, and the organization simply starts lurching from crisis to crisis. This has insidious effects on the organization's culture as we start rewarding our best firefighters. We misalign incentives away from the creation of value and towards the prevention of largely self-inflicted harm.

This is going to burn out your team. People don't like getting paged. They want to sleep. They want to spend time with their families. They want to spend their working hours tackling the cool "hard problems" you sold them on when you recruited them. Ironically, the best firefighters will be the ones to burn out, and then you'll be without them as they either quit or their burnout starts to affect their personalities and performance. (Speaking from personal hard-won experience here!)

So given that we want to build for reliability, how do we get there? Far smarter people than me have given this serious detailed treatment, but from a high level view there are some obvious rough guidelines.

## No More Resume Driven Development

Bleeding-edge technology is broken all. the. time. It's great that your engineers want to learn about Elixir or Vue JS or AerospikeDB. They should do that on their own time, or at least in your internal systems and dev tooling. Don't #YOLO that shit into production!

Not only is this bad for reliability it also tells people that this is good engineering decision making &mdash; that it's okay to push untrusted systems into production. In fact, in many organizations you'll be rewarded for this behavior because you've "shipped". Pay no attention to the unmaintainable tire fire afterwards!

It's not just rewarding the behavior on your team, but it's also a problem for hiring. If your job listings look like a Markov chain from the front page of HackerNews, what kind of developer is this attracting to your organization?

This sort of thing creates a vicious cycle. There are certain people within our profession who never really want to maintain anything. They want to chase the new shiny and then move on to the next thing. If one of these folks lands in your organization and they're allowed free rein, they'll bring in all their friends as well. I've witnessed these roving gangs of locust developers coming in, dropping a new framework or programming language on an organization, and heading off to the next organization to screw up.

Lack of reliability biases your organization against experienced hires. If you've been through a couple of cycles of burnout already (aside: that's super fucked up that this is even a thing), you're going to see a stack of shiny new tech in a job posting and immediately toss it out, because you know there's no way you want to live through that again. It also biases your organization against older folks in general, who will tend to have families at home &mdash; particularly women as they still manage a disproportionate share of household duties. They don't want to be up all night helping you debug MongoDB because you decided to switch to the new storage engine after only a couple of days of testing.

## Choose Boring Tech

We should have a strong bias towards [choosing boring technology](http://mcfunley.com/choose-boring-technology). You have a limited amount of time and energy to pour into innovation. That energy should be spent on the things that will have the biggest positive impact for your organization's mission.

Building for reliability encourages the development of a certain set of cultural values. It builds a culture trust between developers and operators. It builds a culture of inclusivity. It builds a culture of sensible attitudes towards risk. And it builds a culture of work-life balance.

---

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture]({{< ref "2018-02-18-software-defined-culture-0.md" >}})
1. Part 1: Build for Reliability
2. [Part 2: Build for Operability]({{< ref "2018-02-18-software-defined-culture-2.md" >}})
3. [Part 3: Build for Observability]({{< ref "2018-02-18-software-defined-culture-3.md" >}})
4. [Part 4: Build for Responsibility]({{< ref "2018-02-18-software-defined-culture-4.md" >}})
