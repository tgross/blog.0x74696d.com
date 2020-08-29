---
categories:
- development
date: 2020-08-29T12:00:00Z
title: git-send-email
slug: git-send-email
---

Recently _The Register_ [published an
interview](https://www.theregister.com/2020/08/25/linux_kernel_email/)
with Microsoft's Sarah Novotny where she claimed that the Linux kernel
project's reliance on plain-text email was a barrier to entry for new
kernel developers.

Predictably a bunch of folks showed up on Twitter to heap abuse and
gatekeep people's email clients, and just as predictably a lot of
well-meaning folks took the opposing side that because those people
were jerks, that Novotny was right. So I want to talk about both why
the structure of these kinds of arguments is such a disaster and why I
agree with Novotny's stated goals but think that she doesn't have much
of a solution to the problem.

## Misaligned Goals

Let's address the jerks first because they're the least interesting
bit. Novotny's stated goals as Microsoft's representative to the Linux
Foundation board are to ensure the long term survival of the Linux
kernel project and in particular to ensure there's a flow of new
maintainers to the project. It should follow without question that for
there to be new maintainers, there needs to be a flow of new
contributors who eventually become experience contributors who can
take over from the old maintainers as they literally age-out of
working on the kernel full time. I can't think of any possible
good-faith argument against this goal, because it's rooted in the
reality that kernel developers are mortal.

I'm also going to put some words into Novotny's mouth here (in a
friendly sense) and suggest that in referring "developers who have
grown up in the last five or ten years" she's also looking to expand
the _demographics_ of the kernel project contributors. That's a worthy
goal!

But whether or not she intended to imply that, I suspect that many of
the gatekeeping types _think_ she implied it. This is what sets up the
Twitter shitposting, because you have a very noisy group of people who
long-ago staked ground that they want tech to be the domain of cranky
white cis dudes (optionally with beards) and will jump at the
opportunity to fight about it. I find these people super frustrating
both because they're awful and because they suck all the air out of
the room from what could otherwise be adult conversations about the
best tactics. Unfortunately a lot of very smart and empathetic people
that I like get suckered into engaging in that conversation. You can't
reach these people, only freeze them out. (And hope that eventually
they'll do some work on themselves and be ready to join a culture that
is happy to embrace them again, but I'm admittedly cynical about
that.)

## Not Disinterested

The second set of arguments you can have here is that Novotny is not a
disinterested party. She works for Microsoft, and previously worked at
Google. Both of these organizations have reputations for open source
malfeasance and those reputations are going to be reflected onto
anything she says.

If you read the interview carefully, you'll find that Novotny is
talking in fairly broad strokes without really recommending anything
in particular. (This probably contributes to the focus of the
discussion on plain-text email and not maintainer succession) So if
you think that the reputation of Microsoft is well-deserved, you're
not likely to read between those lines in a way that assumes good
intent. Instead, it vaguely smells like another nefarious attempt at
["embrace, extend,
extinguish"](https://en.wikipedia.org/wiki/Embrace,_extend,_and_extinguish).

A similar example might be if Linux Torvalds has something excitable
but borderline to say on the LKML. Because of his reputation as being
an asshole, if you're inclined to see him as a jerk you'll read what
he says uncharitably. Whereas if you're inclined to believe he's
trying to do the work of self-improvement, you may read it more
generously as enthusiastically penetrating questions to a colleague he
respects.

Novotny's playing coy about hosting kernel development on GitHub
probably works against her here. We all know that's what we're talking
about, because there are no technically feasible alternatives for a
project of that scale. (Sorry GitLab.)

In any case, while I'm not particularly inclined to see Microsoft in a
good light, in this case I don't see much to be paranoid about. While
I'm sure GitHub would love the reputational boost of hosting kernel
development, this is small potatoes in the grand scheme of things. It
wouldn't give Microsoft special control over the project that it
doesn't already have by its funding, board position, and many
development contributions.

## Nobody Escapes Conway's Law

If we get rid of misaligned goals or accusations of bad faith, that
leaves us with a discussion of tactics. This is where I suspect
Novotny's background at Google is influencing her to try to apply a
tooling fix to a cultural problem.

Which is to say, `git-send-email` is not the problem here.

Daniel Vetter's 2017 post [Why Github can't host the Linux Kernel
Community](https://blog.ffwll.ch/2017/08/github-why-cant-host-the-kernel.html)
does a good job summarizing the distributed structure of the kernel
development project:

> No one (except Linus himself) is developing stuff on top of Linus’
> repository. Every subsystem, and often even big drivers, have their
> own git repositories, with their own mailing lists to track
> submissions and discuss issues completely separate from everyone
> else.

> ...

> But looking closer, it’s very, very far away from a single git
> repository. Just looking at the upstream subsystem and driver
> repositories gives you a few hundred. If you look at the entire
> ecosystem, including hardware vendors, distributions, other
> linux-based OS and individual products, you easily have a few
> thousand major repositories, and many, many more in total.

As skilled as the kernel developers may be, nobody escapes Conway's
Law. The systems they have developed, _including git itself_, are
reflections of the organization that created them.

The kernel is not developed in the same way that Kubernetes is,
because it's not organized the same way. Kubernetes is largely run by
many committees ("SIGs"), befitting its origin as a corporate
controlled project. While Linux is developed largely via the
contributions of these same corporations, the technical governance
structure is one of distributed hierarchies.

Someone looking to contribute to the kernel needs to understand the
kernel subsystem in question. They need to write professional-grade
C. They need to use the notoriously user-hostile `git` source control
software. Given those heady requirements, I suspect that plain-text
email is not the barrier to entry that Novotny thinks it is. And
certainly compared to understanding the sprawling organization of the
project it seems like a tiny one.

Search for "getting into linux kernel development" and the best page
you find is the
[kernel.org](https://www.kernel.org/doc/html/latest/process/howto.html)
page that gets you started with... kbuild, email patches, and coding
style? A less narrow search found the [development
process](https://www.kernel.org/doc/html/v5.7/process/development-process.html)
page which is better, but not exactly a welcome mat.

This isn't a tooling problem, it's one of human communication. And
what I find especially frustrating about a focus on tooling is that
Novotny's employer is one of those uniquely positioned to contribute
to fixing the human problems.

The huge corporate contributors like Microsoft, Google, and RedHat
should be building on-ramps to kernel development. They should be
producing on-boarding documentation, guides to how the project is
structured, and providing mentorship (and sponsorship!) for new kernel
developers. They should be ensuring that their own pipeline of kernel
contributors is diverse and that the contributors they employ are
building an inclusive culture within the LKML and other project
spaces. And they should be holding each other accountable for doing
the same.

Telling El Reg the issue is plain text email only distracts from
solving the real problems.
