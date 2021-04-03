---
categories:
- development
- golang
date: 2021-01-30T12:00:00Z
title: Single purpose visualization
slug: single-purpose-visualization
---

There's an enormous wealth of data analysis and visualization tools
available, from full-fledged managed services like Honeycomb all the
way down to Python libraries like Matplotlib. These days I'm writing
shrink-wrapped infrastructure software, so when I'm debugging problems
I've been leaning way more to one end of that spectrum: writing single
purpose tools.

I can just barely fool myself into thinking there's a Unix philosophy
at work here about tools that do one thing and do it well. But if I'm
being honest most of these tools turn out to be throwaway because
they're operating at the wrong level of abstraction. I'm solving the
problem immediately in front of me and not worrying about software
architecture unless and until I need it again. Also we're
overwhelmingly a golang shop, so trying to package up Python tools so
that support folks can reuse them is a burden.

A recent example of this a tool I wrote for visualizing metrics from a
Nomad debug bundle. Nomad's ([`operator
debug`](https://www.nomadproject.io/docs/commands/operator/debug))
gathers up a bunch of logs from the cluster and takes a series of
snapshots of the raft state and cluster metrics, and then dump this
whole thing into a tarball. Our support folks can use this for
gathering a ton of data about a customer problem without having to do
a long back-and-forth of questions, and when they need to escalate to
engineers they can hand off the bundle and we can make a first pass at
the problem without bothering the customer some more.

The challenge is that this data is basically just a bunch of Nomad's
API responses or internal structs dumped out to JSON. A bundle for a
complex problem with lots of snapshots can easily be 100MB of JSON to
grub through.

So suppose I want to find how many goroutines are running over time. I
look up the field name in the [metrics
docs](https://www.nomadproject.io/docs/operations/metrics), check the
[`api.MetricsSummary`](https://github.com/hashicorp/nomad/blob/v1.0.3/api/operator_metrics.go#L8-L15)
output for which fields that's going to be under, and I incrementally
massage my way through the JSON with trial and error and `jq` until I
get something like:

```sh
ls nomad/*/metrics.json |
    xargs jq '
        .Gauges[]
        | select(.Name == "nomad.runtime.num_goroutines")
        | .Value
        '
```

Yes, yes. I know I can use `find -exec` instead. Take this and your
"useless use of cat" and leave me alone.

The result is a list of numbers, and if I could understand the
`gnuplot` interface I'd probably pipe those numbers there. But
extracting timestamps from this data structure is really painful in
`jq` and I'll never remember how to do it next time unless I save it
in a script somewhere, etc.

This time I wanted to be able to show this to our support folks, so I
decided to turn it into a single purpose visualization tool that I
knew they could build. I grabbed the `gonum/plot` library, which is
definitely not nearly as nice as Matplotlib but it got the job
done. The resulting tool takes a list of metrics files and generates a
simple SVG (which is pronounced "svig", by the way) for one metric.

If I want to see the latency between the raft leader and its peers, I
can pipe in the list of metrics files and search for that specific
metric:

```sh
ls nomad/*/metrics.json |
    nomad-metrics-plot "nomad.raft.leader.lastContact"
```

And the resulting visualization makes it obvious to me that this
cluster is having latency issues between raft peers: the mean and
maximum latency is well above what's recommended and they have spikes
where the 500ms timeout is being hit, which forces a leader election.

![plot of raft.leader.lastContact metrics](/images/20210130/metrics.svg)

Note that the tool is terrible in many ways: the metric name has to be
an exact match, it has to read in the entire data set every time it
runs, there's no flag on where to send the output file, and it doesn't
open the SVG in your browser for you. But I can put this in front of
someone _today_ without it causing me a huge support burden to get
them spun up on it. And then I can iterate on it over time or abandon
it if something better comes along.

[^1]: This repo that originally went with this article unfortunately had
    to be removed to due overreaching GitHub account policy claims by
    my employer.
