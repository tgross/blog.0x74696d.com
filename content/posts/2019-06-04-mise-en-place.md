---
categories:
- development
- culture
date: 2019-06-03T01:00:00Z
title: Mise-en-Place
slug: mise-en-place
---

>Mise-en-place is the religion of all good line cooks. Do not fuck with a line cook's 'meez' &mdash; meaning his setup, his carefully arranged supplies of sea salt, rough-cracked pepper, softened butter, cooking oil, wine, backups, and so on.

> <cite>&mdash; Anthony Bourdain, _Kitchen Confidential_</cite>

![mise-en-place](/images/20190604/1200px-Mise_en_place_for_hot_station.jpg)

<aside>photo by Charles Haynes - <a>https://www.flickr.com/photos/haynes/500435491</a>, CC BY-SA 2.0, <a>https://commons.wikimedia.org/w/index.php?curid=35488828</a></aside>


It probably comes off as pretentious and tone-deaf as a software engineer to compare anything we do at all to work in the food industry. Most of us have pretty cushy lives in comparison and are far removed from that kind of back-breaking manual labor.

The sole extent of my experience in the food industry is one hot summer of getting up at 4am to open a coffee shop. I'd make lattes for the Philly tourists and office workers until noon, coming home wired, scalded, and with coffee grounds embedded in my fingernails. My primary goal at that age was same as most, which meant trying to pick up the more lucrative closing shift where we served booze and stayed out late afterwards. In retrospect I was terrible at this job and didn't learn any of its essential lessons until much later in life.

## Keep the Plates Moving

That being said, _mise-en-place_ is an awesome metaphor for the day-to-day foundations of software engineering work.

The goal of the production kitchen is to repeatably ship plate after plate at the expected quality level, night after night. The chef takes the measure of the results and adjusts the menu as market conditions (supply availability or customer demand) change. Does this sound familiar?

This is all made possible by the kitchen team having that foundation of _mise_ so that they can focus on the work of production without the distraction of looking around for the salt after each dish.

It is totally possible to ship software without doing it _well_ (as evidenced by... _\*gestures broadly\*_). But the kitchen of our software development lifecycle can really only sing along when we've done it. It's the work we do to make our work better.

What am I really talking about here? In software development, your _mise_ is all the work that's not writing "production" code. It's the design document, the team style guide, a good Makefile, writing tests, and continuous integration and delivery. It's adding hooks for observability. It's writing good commit messages. It's writing good after action reviews and making sure they're shared across the org. All the work that enables our ability to focus and repeatably deliver quality products.


## Stay Out of the Weeds

> If you let your mise-en-place run down, get dirty and disorganized, you'll quickly find yourself spinning in place and calling for backup. I worked with a chef who used to step behind the line to a dirty cook's station in the middle of a rush to explain why the offending cook was falling behind. He'd press his palm down on the cutting board, which was littered with peppercorns, spattered sauce, bits of parsley, bread crumbs and the usual flotsam and jetsam that accumulates quickly on a station if not constantly wiped away with a moist side towel. "You see this?" he'd inquire, raising his palm so that the cook could see the bits of dirt and scraps sticking to his chef's palm. "That's what the inside of your head looks like now."

> <cite>&mdash; Anthony Bourdain, _Kitchen Confidential_</cite>

I'm pointedly avoiding the term "technical debt." Not having your _mise-en-place_ together isn't just technical debt (although it's also that). It's cultural debt. Having a dirty working environment encourages more of the same. What's one more flaky integration test if half the tests are already flaky? And maybe it's not worth even writing that one. The on-call got woken up at 2am by an alarm that wasn't actionable. Ok, we'll mute that alarm for now and it'll be the next rotation's problem.

All this noise is the enemy of deep work. It can lead your team to confuse urgency for importance. That cultural debt is a lot harder to pay down than the technical debt.

## Expediting

Now, there is a particular personality in our industry who really loves to work on their _mise_ but at the expense of its purpose. This is the person who wants to have a 10000 word style guide with detailed rules for how to name variables and which RPC protocol to use in golang before a single line of code has been written. (What? No, this is a "totally" "hypothetical" "example".)

Hopefully in this situation your team can hold each other accountable to their goal. Otherwise you invariably end up with someone acting as expediter to kick everyone in the ass and get them moving. This creates a lot of hard feelings all around, and the team's manager either looks like an ass or ineffectual, depending on how that went down.

## Home Cooking vs Professional Cooking

Another way in which this metaphor is helpful is differentiating between the home cook and the professional line cook. When we're puttering around at home in our kitchens, having a decent _mise-en-place_ can make the work more pleasant. But it's not critical to completing a meal. There's no customer who's going to walk out if their entrée doesn't land by 7pm sharp. There's no requirement for repeatability. With sufficient dedication you can try a new dish every day and if a few flop, no one is going to stop you from cooking for them anymore.

We're the home cook when we're writing software for ourselves. When we rework our blog CSS yet again. When we learn a new language. When we scratch an itch about an open source project we use.

But for the professional, speed and repeatability are vital. Having our _mise_ tight is a requirement for maintaining quality and velocity.

## What Do We Value?

> As a cook, your station, and its condition, its state of readiness, is an extension of your nervous system...

> <cite>&mdash; Anthony Bourdain, _Kitchen Confidential_</cite>

We don't value the _mise-en-place_ processes in and of themselves, but we value the result they enable. But those results aren't merely the artifacts &mdash; the software we write &mdash; but also the way we feel about our work. We shouldn't dismiss the value of flow state, of feeling like the work we're doing is the best we can do. And we shouldn't dismiss that our work can carry intrinsic spiritual or emotional value.
