---
categories:
- development
date: 2022-06-11T12:00:00Z
title: "Platforms are Brownfield"
slug: platforms-are-brownfield
---

The email comes that the newly-formed Platform Team will be migrating
all two thousand of the company's services to the New
Platform<sup>TM</sup>. The new platform will ensure there's a single
workflow across the company for building, testing, securing, and
shipping software. The old legacy cruft that was weighing down
delivery will be swept away. Maybe there's an accompanying slide show
at the all-hands meeting to hype it up. The team has done a proof of
concept with some of the simple services, and will be working with
each service team to get their services ported by the end of the
quarter.

A couple months in, things are moving quickly. The platform team has
taken lessons from product teams and shipped a "MVP" of the
platform. A majority of the company's services are stateless Rails (or
Spring Boot, or Go, whatever) applications that can be shipped in
containers and backed by managed databases. Then the platform team
sits down with the data science team to talk about migrating their
services...

A year or two later, only half of the two thousand services have been
migrated. The New Platform project is far over-budget. Managers of
other teams have complained to the CTO how much toil of the migration
has landed on their own teams. The Platform's performance is poor,
because the team hasn't had time to invest in performance instead of
migrations. Half the Platform team has burned out and quit.

I've seen this play out a handful of times first hand now[^1], and I've
heard this same story from many other folks in the industry. It's not
limited to software-as-a-service delivery; I've seen this happen with
design systems, documentation platforms, and CAD software, to varying
degree.

The conventional wisdom here is that the platform team has done
everything right. They've done the agile thing and started with a
proof-of-concept and MVP. They focused on getting the most business
value out of the platform as quickly as possible, pushing off the long
tail of services for later.

But that long tail of post-MVP services break all the assumptions of
the New Platform. So they end up investing hacking in new capabilities
for exceptions. The platform is all in on containers, but one team
needs nested virtualization. The platform assumes services are
stateless, but one team stores long-running process checkpoints on
disk. The platform assumes Linux, but one team has custom electrical
engineering software written for them twenty years ago that only runs
on MS-DOS, and they don't own the source. That one was fun.

What's going wrong? In the abstract, the promise of the "platform" is
that it'll reduce complexity of a process. But in organizations large
enough to care about platforms, much of the complexity is _inherent_
complexity of the business domain, not incidental complexity.

Developers are lured by the promise of building a greenfield platform,
but building a platform is always brownfield work. Platform
developers, in a rush to simplify a process, are failing to recognize
that they're trying to simplify the _business_. And the business is
going to resist being simplified.

Platform teams can avoid this trap by embracing the inherent
complexity early on. Of course they should start with a simplified
proof-of-concept. But if platform teams are going to borrow concepts
like "MVP" from product development, they should also borrow
"product-market fit". Platform teams should be seeking out the weird
corners of the company to discover the true scope of their project, so
that the platform isn't so rigid that it can't tolerate difference.

At the same time, why is it so important that disparate teams across
the whole company use the same process?  Engineers aren't
fungible. There's no danger that the data science team is going to be
re-org'd next week and turned into web developers, or vice
versa. Centralizing process onto a platform isn't being done for some
abstract value of simplifying things &mdash; it's a decision that the
pain of migration is worth some business value. But migrating the long
tail of applications might no longer match that business
value. Establishing that migrating the long tail of applications is a
non-goal should always be considered an option.

Part of embracing complexity may be accepting that the dream of a
single platform was always just a dream.


[^1]: Certainly never with any of my current or prior employers or
    their customers with whom I have non-disclosure agreements, of
    course.
