---
categories:
- development
date: 2021-05-01T12:00:00Z
title: "Strictly Aspirational Engineering Values"
slug: strictly-aspirational-engineering-values
---

It was before lunch on my first day when I found myself in a
conference room during a total service outage, with thirty or so other
men yelling over each other [^1].

This was particularly alarming because during my interviews we'd
talked a lot about building disciplined incident response culture,
developing deep insight about the platform, and avoiding normalization
of deviance. Clearly, I'd thought, this was going to be a team of
serious professionals. But this was a few years back now and maybe
I've learned a lot since then about seeing through interviewer
bullshit.

Needless to say I didn't even have production access at this point or
know much about the architecture. I'd just gotten my laptop and some
swag from the HR goons, and went to greet my new teammates when some
dude rolled into the office and dragged every man who looked older
than thirty into a "war room." Yeah, only men. Maybe I'll come back to
that in another story.

I found myself reading over some stranger's shoulder, someone who was
yelling less than the others and who had some of the monitoring up on
their machine. There was something definitely memcached related or at
least memcached adjacent going on judging by the conversation in the
room. Without much else to do, I offered my shoulder-surfee help
looking at memcached. I'd had plenty of previous adventures with it,
so if nothing else I could help eliminate it as the source of the
problem.

As it turned out they were using a fully managed memcached service and
only had the metrics that the provider emitted, which wasn't a
lot. The service was definitely in trouble with high latency. The
downstream consumers were a bunch of different web services running on
pre-fork application servers [^2]. The application server processes
could each handle only a single concurrent request at a time, so
latency in upstream services like memcached quickly cascaded into a
full outage.

I noticed the number of connections looked high relative to the number
of processes I'd expect to see running, and then noticed that the
number of _new_ connections was roughly equal to the number of current
connections. A hypothesis started to form that the applications
weren't keeping open their connections and was churning them out so
fast that memcached was burning time queuing those connections.

Without shell access to the memcached host, I asked what monitoring
there was on outbound connections from the clients so we could figure
out which services were causing the problem. There was none. Ok, I
suggested, we'll just script something to ssh onto all the application
cluster nodes, scrape the connections being made to the memcached IPs
for a short window, and then we'll know if it's just one service.

This suggestion was not taken well. One did not simply ssh onto a
host. As it turned out, I was one of only three people in the room who
even had sufficient permissions to ssh onto a host, and two of us were
currently getting hungry waiting for our first day onboarding lunch. I
was getting a serious stink eye from the senior-most engineer in the
room. Even the CTO managed to shut up for, like, ten whole seconds
[^3].

Many many dollars were being burned every minute, so I gently
suggested I could take my new best friend and we could go poke at the
memcached client out of the way of everyone else. We got the go ahead
and I scrambled to get my laptop properly authorized so we could shell
into an application server node.

The dude who I'd been shoulder surfing was now shoulder surfing me. We
were looking at `netstat`, querying memcached stats via `telnet`,
measuring `connect` syscalls via BPF, and getting good confirmation of
the hypothesis. You'd have thought I'd introduced fire to this guy. To
be clear, this was an organization with lots of senior talent that
proudly hired tons of folks from Google (and was quick to remind you
of it). But asking the operating system what was wrong was just not
something people did here.

We'd found which service was causing the problem, and now the trick
was to figure out what was wrong with it. Here's where I think the
various expense but very powerful observability services
(ex. Honeycomb) would have come in handy, but we didn't have anything
like that. Most of the war room broke off to isolate the buggy service
and clean up the damage. My buddy and I started digging into the
service's memcached client. Naturally this was a third party library
selected in ages past by the company founder, primarily on the basis
of GitHub stars. And as far as anyone knew, no one had ever reviewed
its internals. Which was unfortunate because I wasn't even familiar
with the language and we found a bug in the connection pool logic
within fifteen minutes of looking at it. This wasn't even _the_
problem though. That was so much worse.

The logs querying service was truly wretched and I can only assume was
chosen on the basis of price and price alone. But now that we knew
what service was misbehaving, we could get the log volume to search
over down to something reasonable. Only to immediately find that the
application server's worker processes were in a slow restart loop.

Pre-fork application servers for interpreted languages often have an
interesting design feature where they just blithely assume you're
going to leak references all over the place, and so they let you
configure a limit on the number of requests or amount of memory for a
given worker. When the process reaches that limit, the main process
signals it to stop and replaces it with a fresh one. This is fun if
you're running the application server in a container (which we were),
because the memory limit of the container needs to match the sum of
the memory limits of the workers, plus enough for the main process, or
it'll randomly OOM instead.

The application server was starting a worker, the worker would eagerly
open a pool of memcached connections (for the single threaded
program!) and proceed to request a whole mess of _huge_ blobs of
cached data at startup. The cached data would get deserialized to
giant in-memory hashmaps. The application would manage to serve only a
handful of requests before blowing the top off the worker memory limit. The
main process would kill it, and start another one to replace
it. Repeat until outage.

It's a cheap shot to point out that this wasn't being
monitored. Applications and the OS and machine that hosts them can
produce nearly arbitrary volumes of metrics and logs. The cost to
ingest and analyze _all_ that data could easily exceed the business
value of the service, so you have to make compromises. But... I feel
like it's not unreasonable to draw the line well before "we're not
going to notice if the application is constantly restarting".

In any case, I say to the room "well there's yer problem." The
consensus in the room was that the solution was to bump the limit on
the application server and its container. It gets doubled, and the
outage is over.

I finally get to have my onboarding lunch with my team, and I ask how
we typically notify the team that owns the misbehaving service to fix
it. The answer was that we didn't. Service teams didn't care to know
what resources they were using, and the platform team didn't care to
know what the normal behavior was supposed to be. All over the
organization, there were dozens of services in this state. They'd just
continue to consume more and more resources until they caused an
outage, and that was it. We were adding many more developers and many
more services, without adding any additional observability or
incentive to care about the problem. The platform and infrastructure
teams were getting paged two and three times a day as a
result. Deviance had been completely normalized, at the expense of
both the business and the human beings who had to clean up the mess.

It should come as no surprise that this was the first of many such
incidents during my tenure. The yawning gap between the team's
aspirational values and their practice never closed. When an
organization shows you who they are, believe them.


[^1]: Some small details of this story have been altered to protect
    the innocent, to paper over gaps in my memory, or for comedic
    effect. Unfortunately the first sentence of this post is not one
    of those details and is absolutely true.
[^2]: I'm being deliberately vague here but if you've used Django on
    gunicorn without gevent or Rails on unicorn rather than puma,
    that's the sort of thing I'm talking about.
[^3]: This is an example of changing details for comedic effect. He
    actually shut up for five seconds, at most.
