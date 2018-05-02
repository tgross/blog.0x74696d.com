---
categories:
- culture
date: 2018-05-02T01:00:00Z
title: A Hotdog is Not a Sandwich
slug: a-hotdog-is-not-a-sandwich
---

I was recently visiting lovely Austin, Texas. During a dinner with some friends, one of the non-techy folks at the table was getting hopelessly bored by our yammering on about blockchains or whatever, so I changed the subject to something more fun: the important debate over whether a hotdog is a sandwich.

On the one hand this is just a silly meme, but it's also a convenient social shortcut. You get to learn about how someone thinks about problems, how they debate, something about their cultural context, if they have a sense of humor, if they're pompous windbags, or if they're the sort of person who corrects "less than" to "fewer" (but I repeat myself). More importantly, there are no stakes. No one's career, business, or identity is tied up in whether a hotdog is a sandwich.

The hotdog debate also serves as a shortcut for talking about how we in the tech industry use language.

## Precision

You've probably heard the adage "there are two hard things in computer science: naming things and cache invalidation." When we write software, names are important to how we communicate our intent. Whole chapters of classic books like Steve McConnell's *Code Complete* are devoted to naming things. Some folks go so far as suggest you shouldn't comment software because names of your types and functions should make everything obvious. (I think that sounds nice for greenfield web applications but maybe not so much for systems software where you might need a long [essay](https://github.com/joyent/illumos-joyent/blob/master/usr/src/uts/common/io/mac/mac_sched.c#L29) to explain the design to future generations.) We mostly all agree on the importance of names and definitions in that narrow context.

Where we get into trouble is when we try to apply that precision more broadly. To paraphrase the folk singer [Utah Phillips](https://en.wikipedia.org/wiki/Utah_Phillips), language is like a river. We put our concepts and experiences into the river and they flow away from us, until they no longer have our identity &mdash; they have their own utility. And others can borrow those notions to use in their own context. Language bridges the gap between me and another person, but it's also a source of confusion because words get muddied in the river.

Most people quickly figure out that in order to say a hotdog is not a sandwich, that you need to have shared definitions of "hotdog" and "sandwich" in the first place. But the precision of that definition is only needed when you're trying to differentiate. If we're standing next to a table with a hoagie, a glass, and a fork, and I say to you "please pass me that sandwich," you know exactly what my intent is even if you don't think a hoagie is really a sandwich. You're not going to be suddenly confused and hand me the fork. Even if you're from Europe or Asia and have no idea what the hell a hoagie is (or a hotdog for that matter), you're probably pretty sure from the context I meant the sandwich-looking thing.

It's also much harder to agree on exact definitions when the concept being discussed is abstract. In our hotdog case, you can generate vigorous debate on the definition of something as concrete as a sandwich! The more abstract the concept, the less likely it is that you're going to have universal agreement on it. "What is a hotdog?" Ok. "What is a sandwich?" Hm. ["What is love?"](https://www.youtube.com/watch?v=HEXWRTEbj1I) Uh...

The important thing in any given conversation then is not some canonical definition of a word, but the definition that's being shared (by understanding or even just temporary agreement) by the folks in that conversation. Where this gets tricky is when words are tied up in agendas and identity.


## Agendas

The hotdog industry probably doesn't care whether anyone thinks a hotdog is a sandwich. I can't see this being a matter of intense debate in the boardroom at Hofmann's. If anything they probably love the meme just because it gets people thinking about hotdogs.

But in our industry there are lots of folks who do have agendas around definitions. The source of this is mostly an attempt at differentiation. Imagine you are an artisanal butcher making [coneys](https://en.wikipedia.org/wiki/White_hot) instead of hotdogs. You need to stand out from vast crowd of folks making hotdogs. You don't want your product to be confused for hotdogs, particularly because if someone is coming to you for a hotdog they're going to have a novel and amazing experience but maybe not what they thought they wanted. Maybe they'll then turn around and say to other prospects "they make weird hotdogs." Disaster, right?

I once worked with a team that had this "underdog syndrome." Because they were a small team their offering wasn't as feature rich as the leading competitors. But instead of focusing on their strengths, a lot of their content marketing efforts were focused on playing games with definitions. On one hand you can try to parlay this into attention for your organization, and that can work. But it can also result in you having public disagreements with competitors about the definition of "standards" or "monitoring", which makes everyone involved seem out of touch.

The worst case of this is when a team tries to take an existing term of art that's broadly agreed-upon and tries to forcibly change the definition to match what they do. I consulted recently for a team that's a bit disconnected from the wider industry that was trying to redefine things like "PKI" and "serverless." This was not going to go well!

Your customers don't care about your definitions. They care about *their* definitions! Yes, it's sometimes important to educate your customers to make them more successful. But creating distance between vendor and customer isn't what you want &mdash; you have to reach them where they are.


## Identity

The most hard-to-shake agenda is personal identity. If your identity is tied up in a particular definition it makes it much harder to bridge the gap of understanding and have a conversation about the underlying concept. You'll need to bring everyone to your particular definition first. If you find yourself doing this a lot, step back and examine whether you intended to make that definition part of your personal identity. If someone is being particular about definitions for no obvious reason, step back and consider whether you're threatening their sense of identity in the process.

Suppose one day the folks who grill hotdogs for a living came to the butchers who make hotdogs and said "if we work more closely together we can produce a better tasting-hotdog more quickly, and with less stress and more money for both of us." And the teams who got really into this decided to call it ButcherGrills, a marrying of the making of hotdogs with their delivery. Pretty cool, right? Well at some point the large hotdog manufacturers see this and say to themselves "we need this ButcherGrills stuff, can we hire people to do it?" And so they start hiring people and give them the title ButcherGrills, because if they hire grillers or butchers who don't know about the ButcherGrills methodologies they'll have to train them and as big companies they'd rather die than ever train anyone to do anything.

Now we're in a situation where there are people who are _doing_ ButcherGrills and another group of people who are calling _themselves_ ButcherGrills. The second group is never going to agree with the first group because their career is built around being "a ButcherGrills". Not to mention that ButcherGrills roles seem to pay a lot better than griller roles.

What is to be done? We can try to play with definitions some more; we need a new category of folks who are Hotdog Grillability Engineers. Maybe that's useful if it adds anything new to the discussion instead of being co-opted to mean the same thing that ButcherGrills did. But is the definition all that important? Or is it only important that we share _some_ definition with the folks we're communicating with?

More importantly, what's it to me? If someone's identity is tied up in a definition that means it's important to them. Unless I have my identity tied up in a different definition, it literally costs me _nothing_ to accept someone where they are. (And if I do have my identity tied up in a different definition, it's on me to examine myself about whether this definition is healthy, whether it's tied up in ego or privilege, etc.) If someone says that their title is ButcherGrills, who am I to say "well that's not what ButcherGrills really is"?

The most important definitions for us to agree upon are the ones that folks assign to themselves. Whether someone self-identifies as a sysadmin, devops engineer, or SRE; whether they self-identify as a he, her, or they; or whether they self-identify as working in observability, monitoring, or logging; we start from a better place of empathy and understanding if we take those identities as a given and work together from there.

But a hotdog is still not a sandwich.
