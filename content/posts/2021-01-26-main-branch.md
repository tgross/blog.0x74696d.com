---
categories:
- development
date: 2021-01-26T12:00:00Z
title: Main Branch
slug: main-branch
---

A short and mostly unserious rant.

Much of the industry seems to have come around to changing the default
branch for git from `master` to `main`. It's absolutely terrible. Oh,
not changing from `master`. That's fine. A modest improvement in
making our industry kinder. I'm all for it. But we picked `main`.

Literally any time anything to do with git comes up, you've got a
whole mess of people complaining about what a terrible user experience
it has, and how hard it is to bring new people into the industry when
we use such unfriendly tools, and yada yada yada. And they're mostly
right.

The git data model is awesome, but the command line interface is an
inconsistent disaster that we're all begrudgingly forced to learn. I
feel like I have a really solid understanding of the data model and
I'm a rebasing and reflogging fiend, but I still end up having to
double-check the man page every time I get away from the twenty or so
commands I use on a regular basis. But we all recognize how hard it is
to change software that's been in widespread use. Backwards
compatibility is important.

So there we were as a whole software industry, faced with a rare
opportunity to break free from a legacy decision...

And we picked `main`.

Main? _Main!?_

The correct answer was `trunk`.

Obviously.

Choosing `main` is exactly the sort of short-term local-maxima
thinking I've come to expect from the industry. It's short, and it
preserves some muscle memory from `master`. So you're saving typing
one (1) character over `trunk`, assuming you're not a professional
with shell completion. And you're preserving muscle memory, which only
makes a difference during the month or so after your team has switched
away from `master`, and only for the _set of people who are currently
using git_. It means nothing to the umpteen million people who will be
coming into the industry over the next several decades (at least!)
that we'll be using git.

Instead, we could have chosen `trunk` and made some tiny marginal
improvement in the beginner's mental model for all those people. And
calling the default branch `trunk` is _fun_. Have some fun for fuck's
sake. A `main` branch is dry toast.
