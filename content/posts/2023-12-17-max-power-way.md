---
categories:
- development
date: 2023-12-17T12:00:00Z
title: "The Max Power Way"
slug: max-power-way
---

In a 1999 episode of the Simpsons, Homer briefly changes his name to Max Power
in a bumbling attempt to adopt a more successful persona via nominative
determinism. The episode contains this memorable exchange:

> Homer: "Kids, there's three ways to do things. The right way, the wrong way,
> and the Max Power way!"
>
> Bart: "Isn't that the wrong way?'
>
> Homer: "Yeah, but faster!"

That pretty much sums up my take on the value of Large Language Model (LLM)
coding assistants.

I'm mostly interested in two broad categories of criticism of LLMs. LLMs are
tools and we can talk about their value _as tools_ independently of any other
criticism. And then there's the social impact of introducing those tools in the
context of our industry. All the "AGI breakout" science fiction is deeply
unserious.

<aside>Addendum (2023-12-18): there's a whole <em>other</em> thing we can be
critical about, which is the fast-and-loose relationship LLMs have with
intellectual property. But I'm going to intentionally punt on that for another
day.</aside>

As tools, LLM coding assistants... just aren't all that impressive? Sure,
there's definitely an initial "wow" moment. But then you realize that a lot of
the code they generate is poor. This isn't unexpected. LLMs are trained not only
on the "best" code but on all available code, and the typical code you can grab
from a random repo is honestly pretty crap.

LLMs have no understanding of your business domain, so I've seen LLM suggestions
that are syntactically valid but just utter nonsense in the context of the work
to be done. What makes this worse is the autocomplete-style UX of the typical
tooling, so pairing with someone running VSCode with CoPilot and discussing a
tricky business domain problem is like having the worst PM in the world shouting
bad ideas the entire time.

Large bodies of boilerplate code seem like worthy targets for LLMs. But this
carries extra risk, because code that's monotonous and repetitive is exactly the
kind of code humans are terrible at catching bugs in. This kind of problem is
better solved by deterministic code generation from interface definition
languages (IDL), like generating services from protobuf specs.

Languages like Go also seem like promising targets for LLMs, because the
language itself fights against abstractions and is repetitive and tedious to
write. But it seems like every non-trivial Go project ends up building those
abstractions anyways because it helps so much in _reading_ the code. Go is
"simple" (to a fault) but this means reading it is like reading through a
straw. LLMs don't have enough context to build the kinds of whole program
abstractions you want. And it seems that the average example online of Go's
semi-structured concurrency with channels has subtle deadlocks, if the errors
I've seen output by LLMs are to be believed.

I've seen an argument that a LLM assistant is like having a junior programmer
writing the code. You stand in for the presumably more experienced engineer who
reviews and corrects as it goes. Except unlike a junior it doesn't learn except
by retraining. If I had to correct a particularly dull junior engineer
repeatedly for the same mistakes, I might gently steer them into a career in
management.

That "junior assistant" model isn't all that accessible to the junior engineer
themselves, either. Human beings can learn skills by watching others do them. If
I had to guess, watching the output of a machine is worse for learning than
watching another human performing a skill because of all those nice mirror
neurons we have. But it doesn't matter because humans _master_ skills only by
doing them. A junior engineer leaning on a LLM won't develop the skills they
need to determine if the output of the LLM is any good.

And that leads directly to the wider social problem. If the hype around LLMs
allowed them to be just another tool in our toolbox, we could use them (or not)
and it'd be a question of engineering tradeoffs. Most tools that fail to perform
at the rate LLMs do are quickly set aside, brought out only for the narrow
niches in which they work well. But a whole lot of people are buying into a hype
that LLMs are a massive paradigm change that will disrupt the industry.

Now, there's a few folks in the industry who are cheering on some kind of giant
upheaval where millions of engineers lose their jobs. Maybe they think they'll
be among the anointed few spared by the techno-fascists running OpenAI or
whatever. No surprises there; every regressive movement co-opts a bunch of the
targeted group, class traitors who we should encourage to go play in traffic.

Because management culture treats workers like interchangeable cogs, we should
expect that some organizations will try to replace workers with LLMs. Some
companies will decide that they can get rid of all their expensive senior folks
and just have cheaper juniors, or outsourced body shops, doing all the work with
LLM assistants. I'm sure the compliance-security-industrial complex is already
eagerly spinning up new product lines to solve the resulting disasters from
that. Other companies will go the other direction and decide they can get rid of
all their junior folks and multiply the effort of senior folks with LLMs. But
without a pipeline of junior engineers, you eventually have no senior engineers.

The successful organizations will be those who recognize that there's a
neverending backlog of creative work to be done, and that creative workers can't
be replaced by stochastic parrots. LLMs are just one tool and like all choice in
tools, those closest to the work should be left to decide whether they are the
right tool for the job. But recognizing that requires the kind of long horizon
thinking that's notably absent from most companies. It may be up to tech workers
to organize to make that future happen.


<!--  LocalWords:  LLMs
 -->
