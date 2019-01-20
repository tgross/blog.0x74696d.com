---
categories:
- talks
- culture
date: 2018-02-18T04:00:00Z
title: Software Defined Culture, Part 4 - Responsibility
slug: software-defined-culture-4-responsibility
---

This five-part series of posts covers a talk titled _Software Defined Culture_ that I gave at [DevOps Days Philadelphia 2016](https://www.devopsdays.org/events/2016-philadelphia/program/tim-gross/), [GOTO Chicago 2017](https://gotochgo.com/2017/sessions/43), and [Velocity San Jose 2017](https://vimeo.com/228067673).

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture]({{< ref "2018-02-18-software-defined-culture-0.md" >}})
1. [Part 1: Build for Reliability]({{< ref "2018-02-18-software-defined-culture-1.md" >}})
2. [Part 2: Build for Operability]({{< ref "2018-02-18-software-defined-culture-2.md" >}})
3. [Part 3: Build for Observability]({{< ref "2018-02-18-software-defined-culture-3.md" >}})
4. Part 4: Build for Responsibility

---

# Building for Responsibility

This has been the section of the talk where I definitely lost some of the audience. In fairness, you were warned at the beginning that we were going to talk about culture and that it can be tricky. So if you've been following along so far and don't think I'm totally crazy yet... hold on to your butts!

## Every Tool Comes With a Community

All our technical choices implicitly make us a part of the community of users of the tools we choose. Some of those communities have been intentionally and thoughtfully designed around making sure that everyone can participate in the community. The Rust language community is an amazing example of this. From the very beginning of their organization, they realized that the technical community would be stronger when everyone takes responsibility towards making it inclusive. From their [Code of Conduct](https://www.rust-lang.org/en-US/conduct.html):

> Even if you feel you were misinterpreted or unfairly accused, chances are good there was something you could've communicated better &mdash; remember that it's your responsibility to make your fellow Rustaceans comfortable.

Now, I'm not saying you should go and switch all your production code to Rust. I did recommend in Part 1 to choose boring technologies, after all! But it's clear that the Rust community has taken seriously its responsibility to be welcoming to all.

Other communities have well-deserved reputations for toxicity. When you choose a technology where a portion of the community forked the runtime in protest of the steward company's CTO defense of gender-neutral pronouns in documentation, you're implicitly saying you're okay with being part of that community. Maybe that's the right choice because the rest of the community outweighs the sexist assholes. But we should make those trade-offs with open eyes.

When you choose a language where the original developers defend their language design decisions because their co-workers are ["not capable of understanding a brilliant language but we want to use them to build good software"](https://channel9.msdn.com/Events/Lang-NEXT/Lang-NEXT-2014/From-Parallel-to-Concurrent), then you shouldn't be surprised if this mentality has trickled into the community.

When we choose a technology for our organization, it determines what communities we'll be a part of. It determines who we'll hire. If your organization's mission is to build amazing compiler tools, then you might want to hire people who know that "a monad is a monoid in the category of endofunctor" (not me!). But if you're making line-of-business CRUD web apps that mostly serialize rows in and out of a database, you might not want to choose Haskell. Not because of any technical constraints, but because the community of developers you'll have access to are going to be bored out of their minds writing line-of-business CRUD web apps.

## Community Doesn't Stop With Your Team

Our technical communities are only one part of building with responsibility in mind. There is also the larger community &mdash; our culture at large. The culture impact of our technical choices reflect our biases and they reflect our blind spots. When Google and Facebook demand the legal names of users, it's because they're not considering the risks that political activists, abuse victims, or trans persons would be taking by giving this information up. When a media website pushes down 10MB of crummy ads to go along with 100 words of news content, it's because they're not considering the impact this has on working class users with low-end limited data plans, who can't afford the stuff in those crummy ads anyways.

[![Kalanick keeps asking for unethical/illegal things, but at some point we have to talk about how engineers at Uber keep saying yes.](/images/20180218/marco-rogers.png)](https://twitter.com/polotek/status/856183297180704768)

When I gave this talk, I asked the audience to stop and reflect on what they were doing on a day to day basis. Am I making the world worse? This can be for whatever definition of "worse" you want to use. Maybe you're ok with ads, but not pharmaceutical ads. Maybe you're ok making embedded software for sensors but not for weapons. Maybe you're ok making weapons, so long as the software that delivers them is Free and Open Source. But whatever your definition is, you can ask yourself this question.

I then ask how many people work for organizations that are hiring. In a packed room of hundreds of people, virtually every hand goes up. If you think you're making the world worse, the market conditions in our industry are such that you don't have to continue to participate in that. Find somewhere that doesn't make the world worse.

## Professional Ethics

The software industry doesn't have a professional licensing body. That's probably the right call, at least for now. There's so much variation in what we do &mdash; the people who write web apps and the people who build embedded systems for airplanes are only barely in the same profession. But other industries do have licensing bodies, and I think we can learn a thing or two from our siblings in other professions.

> Engineers shall hold paramount the safety, health and welfare of the public and shall strive to comply with the principles of sustainable development... Engineers shall act in such a manner as to uphold and enhance the honor, integrity, and dignity of the engineering profession.

This is from the [Code of Ethics for the American Society of Civil Engineers](http://www.asce.org/code-of-ethics/). Imagine what the software industry would look like if we held to this code of ethics. Imagine if we had [shared principles](https://www.youtube.com/watch?v=9QMGAtxUlAc). Imagine how it would change the impact we have on the world. We don't need a governing body to impose this on us.

We can start today.

---

If you'd like to read the rest of the series:

0. [Part 0: Software Defined Culture]({{< ref "2018-02-18-software-defined-culture-0.md" >}})
1. [Part 1: Build for Reliability]({{< ref "2018-02-18-software-defined-culture-1.md" >}})
2. [Part 2: Build for Operability]({{< ref "2018-02-18-software-defined-culture-2.md" >}})
3. [Part 3: Build for Observability]({{< ref "2018-02-18-software-defined-culture-3.md" >}})
4. Part 4: Build for Responsibility
