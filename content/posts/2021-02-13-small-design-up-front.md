---
categories:
- development
date: 2021-02-13T12:00:00Z
title: "Small Design Up Front"
slug: small-design-up-front
---

At my current gig and several before that, the initial engineering
design document is the Request for Comments (RFC), sometimes called
the [Request for Discussion](https://github.com/joyent/rfd) (RFD).

If you've been reading the series on building a ZFS plugin for Nomad,
you might have asked yourself if this kind of stumbling through the
design is typical of the RFC documents I've written. But that series
is really about all the design work that happens before the initial
design is documented. It's brainstorming, hypothesizing, and
exploration. The first draft of a RFC is the output of that work, so
typically by the time anyone else has seen it hopefully the obviously
dumb ideas and dead ends have been weeded out.

The RFC ends up being a good "sandbox" for a small up-front design
process. I suspect it's especially valuable for system software where
even a minimal experiment can be costly. And the structure discourages
you from trying to come up with a rigid specification that's doomed to
be invalid the moment you start implementing it.

In some sense you're writing a RFC to communicate to your peers what
you've already figured out about the problem. Their time is a gift,
and the most valuable feedback to get is that which you couldn't think
of on your own. So you should invest the time to ensure they're not
just going to tell what you should already know. In a healthy
organization, writing is a way to collectively discover the design,
rather than persuade the team.

The phrase "in a healthy organization" is doing a lot of work
here. I've worked places where RFC discussions were more of a battle
ground for interpersonal conflict and office politics than meaningful
engineering discussion. In that environment you end up writing
defensively to head off debate and hide implementation details that
will trigger objections. These documents are better named Request for
Permission. And if you're in this situation... well, writing RFCs ain't
gonna save you.

I'm probably a weird outlier, but I even write RFCs for personal
projects. Call it writing as structured thought experiment. It's a
tool, and one that supplements rather than replaces a whiteboard
diagram or a throwaway spike. I could easily throw it out as soon as
it's done, but why not keep it?

There can be a few audiences for those artifacts. A project might get
completed to the point where it could be open sourced, in which case
having those early design documents would be valuable to users or
contributors. But the most important audience is Future Me. My level
of interest or volume of work on these projects ebbs and flows. I
might take a project through the initial design, feel like I've
explored the problem well enough to learn what I wanted to learn, and
set it aside for months. The RFC is like a well-written commit message
for the project as a whole.
