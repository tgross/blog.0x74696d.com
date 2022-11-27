---
categories:
- development
- ux
date: 2022-11-27T18:00:00Z
title: "Two Kinds of UX Blunder"
slug: two-kinds-of-ux-blunder
---

The house we rent has high ceilings along with lots of ceiling fans,
which is great for the warm months here in Philadelphia. Most of these
are the pull-cord type: a wall switch powers it on or off and then
there are two pulls that toggle the lamp and set the fan speed. But
the one above our dining room tables has a remote control, and it's a
good illustration of two different kinds of UX blunder.

First let's set the stage. The image below is the remote control,
stuck to the wall with velcro tape. It's battery-powered and
presumably communicates via radio in the ISM band, like a garage door
opener or most other household devices.

![A ceiling fan remote control. It has five rubber buttons, four of which control the fan speed and the last which controls the lamp](/images/20221127/remote.jpg)

The buttons are cheap and squishy rubber, with a lot of give before
they activate. There's a small red LED above the buttons indicating
that a button has been pressed, but there's a delay of a half second
or so before anything actually happens on the fan overhead (and in any
case, the fan is behind you and overhead when pressing the buttons so
you can't see what's happening and the red light at the same
time). The relevance of this will be obvious in a moment.

The four buttons towards the top of the remote control the fan. The
icons are three dots for the fastest speed, two for the second
fastest, and one dot for the lowest. The icons are raised to be
discernable by touch, and the fan speed buttons are even ever so
slightly different sizes. The fourth button shows the [IEEE 1621 power
symbol][], which turns off the fan. It does not turn the fan back on,
but that's not even the worst use of iconography I've seen _today_ so
we'll give that a pass.

The last button has a sun-like icon which toggles the lamp. We noticed
when we moved in that the lamp was not very bright so we brought in a
few of our own light sources as well.

One day a few months after moving in, I come downstairs and my spouse
informs me that there's something wrong with the ceiling lamp. As the
professional software meddler of the house it obviously falls upon me
to debug this. I press the button and the lamp is incredibly dim
&mdash; like a flickering candle. So I turn it back off, get the
ladder, and take off the globe. Only to find that none of the bulbs
are blown. Just dim. I push the button to turn them back on. Strange,
it seems like they were even dimmer now? And was it just my
imagination or was the delay from the remote longer than normal? I try
again, firmly holding down the button this time. Suddenly the lamp
flares to life!

The button is a dimmer switch.

The first UX blunder here is the easy one: discoverability. Nothing
about the interface of the remote suggests in any way that the lamp
was dimmable. Having multiple buttons for fan speeds but only one for
the lamp indirectly suggests that the lamp is _not_ adjustable. Now,
I'm sure that there's a paper instruction booklet that came with the
fan that explains this. But this is a cheap ceiling fan bought by a
landlord years ago for a house he minimally renovated to rent
out. That instruction booklet is long gone.

The software industry is mildly obsessed with
discoverability. Arguably this is economically incentivized. If you're
burning piles of money for hyper growth to bring on new users (while
vaguely ignoring the cohorts that churn out), discoverability is your
life blood. It's largely what determines "time to value".

But now my spouse and I know how the dimmer works. Within the limited
design space of this interface, we've become "power users." Which
means the overhead lamp is always set to the exact brightness we want
it and we never dim the lamp when we mean to turn it off, right?

No! Because the second blunder here is an interface that encourages
user error. The affordance of the button is overloaded &mdash; it does
more than one thing. And feedback is delayed, so when you intend to
shut off the lamp you need to press long enough to know that your
command has been received, but not too long such that the remote
interprets this as a command to dim the lamp. You can understand
exactly how the interface is intended to work and still misuse it on a
regular basis.

This kind of UX problem is overlooked in the software industry. The
user's mental model for software breaks down because the model isn't
reliable. Cause and effect become divorced by poor performance, opaque
asynchronous actions, and eventual consistency. Conversely, software
can have middling discoverability but work so reliably that once users
get over the learning curve they won't give it up. Software that
allows users to become experts is software that survives the test of
time.

[IEEE 1621 power symbol]: https://en.wikipedia.org/wiki/Power_symbol
