---
categories:
- development
- nomad
- golang
date: 2021-02-07T12:00:00Z
title: "A ZFS Device Driver for Nomad, Part 1"
slug: zfs-device-driver-for-nomad-part1
---

After yesterday's post, my colleague Chris Baker
[Tweeted](https://twitter.com/ScaredOfGeese/status/1358126170236203011):

> I'm especially curious whether the device lifecycle is gonna give
> you the hooks you need without hacks.

Ominous foreshadowing.

The first challenge I identified in the device plugin API was that the
plugin gets a list of device IDs in the
[`Reserve`](https://www.nomadproject.io/docs/internals/plugins/devices#reserve-deviceids-string-containerreservation-error)
method, but the scheduler only knows what device IDs are available
from the fingerprint. That's going to make it awfully challenging for
the job submitter unless we create the datasets ahead of
time. Coincidentally, this is similar to what we face with
[CSI](https://www.nomadproject.io/docs/internals/plugins/csi) in
claiming a unique volume per allocation. That's going to require
scheduler changes, which I'm working on in
[nomad/#7877](https://github.com/hashicorp/nomad/issues/7877#issuecomment-772552412). So
maybe that implementation for volumes should take into account wanting
to apply "unique per allocation" interpolation to other resources.

Assuming we somehow solve that problem, there's another that comes to
mind. I'm looking at the API for the device plugin and I see `Reserve`
without a mirrored method to release the claim when we're done with
it. And if we're reserving a device, shouldn't it be for a particular
allocation? Then I see this part of the
[docs](https://www.nomadproject.io/docs/internals/plugins/devices#lifecycle-and-state):

> After helping to provision a task with a scheduled device, a device
> plugin does not have any responsibility (or ability) to monitor the
> task.

Hold up. This is reminding me of the old Seinfeld bit about how anyone
can just take reservations. How does this actually work?

Now at this point you might be asking yourself how an experienced
engineer who's been working on a code base all day every day for a
year and a half can simply _not know_ how a feature like this
works. Some of that is size: Nomad is 400k lines of go code, plus
another 50k or so of JavaScript, not counting vendored
dependencies. Roughly half of that is tests. That's a lot to digest.

But Nomad is also reasonably well-architected (with plenty of room for
improvement, of course!). Many features can be implemented as discrete
"hooks" that get called by the various event loops. So once you get
one of those features working you can mentally unload that context and
it will need minimal maintenance. Abstraction of components isn't good
just for the sake of it, but because it lets mere mortal developers
like me build software solving galaxy brain problems.

With that out of the way, let's look at what's happening under the
hood with the device plugin API. Note that throughout this section I'm
linking to a specific tag so that the line references don't change
over time. If you're reading this much later, you may find you want to
look for the same functions at different line numbers on the current
version.

Each Nomad client has a device manager that runs the device
plugins. Each instance it tracks runs a fingerprint: one at start and
then periodically. The [instance
fingerprint](https://github.com/hashicorp/nomad/blob/v1.0.3/client/devicemanager/instance.go#L338)
asks the plugin for a
[`FingerprintResponse`](https://github.com/hashicorp/nomad/blob/v1.0.3/plugins/device/device.go#L40-L48).
We get back a list of devices, which according to the docs we're
supposed to assume are interchangeable from the perspective of the
scheduler.

The fingerprint goes up to the device manager, which calls its
[`updater`](https://github.com/hashicorp/nomad/blob/v1.0.3/client/devicemanager/manager.go#L191)
to add the fingerprint to the client node's state. This makes its way
via the
[`Node.UpdateStatus`](https://github.com/hashicorp/nomad/blob/v1.0.3/nomad/node_endpoint.go#L375)
RPC to the server, where it finally gets persisted as a
[`NodeDeviceResource`](https://github.com/hashicorp/nomad/blob/v1.0.3/nomad/structs/structs.go#L3066-L3074)
in the state store along with the rest of the client's resources. At
this point, the servers know what devices are available on the
client. This is the root of our problem around unique device IDs; the
plugin is telling the server what device IDs are available, and not
the other way around.

Now let's see what happens when we try to schedule a job with one of
these devices. I'm going to skip past most of the scheduler logic here
but check out my colleague
[schmichael's](https://github.com/schmichael) awesome [deep
dive](https://www.youtube.com/watch?v=m6DnmVqoXvw) if you want to
learn more. tl;dr we eventually get to a point where the scheduler has
to rank which nodes can best fulfill the request. In the ranking
iterator we attempt to get an
["offer"](https://github.com/hashicorp/nomad/blob/v1.0.3/scheduler/rank.go#L357-L360)
for that device. The
[`AssignDevice`](https://github.com/hashicorp/nomad/blob/v1.0.3/scheduler/device.go#L29-L32)
method checks the placement's
[feasibility](https://github.com/hashicorp/nomad/blob/v1.0.3/scheduler/feasible.go#L1264-L1288),
or whether the node has enough of the requested devices available that
match our constraints. But note that the scheduler is checking that
the _server's_ state of the world says that we have enough of the
devices, and not communicating with the plugin at this point. Nomad's
scheduler workers always work with an in-memory snapshot of the server
state and don't perform I/O until they submit the plan to the leader.

So when do we talk to the device plugin? Once the plan is made and the
client receives a placement for the allocation, the client fires a
series of hooks for the allocation and all the tasks in the
allocation. The [device pre-start
hook](https://github.com/hashicorp/nomad/blob/v1.0.3/client/allocrunner/taskrunner/device_hook.go)
is what finally takes the list of device IDs and calls the plugin's
[`Reserve`](https://github.com/hashicorp/nomad/blob/v1.0.3/client/allocrunner/taskrunner/device_hook.go#L48-L49)
method.

But just as we suspected from the plugin API, there's no matching
post-stop hook. The Nomad server is responsible for keeping track of
whether or not a device has been reserved. Which makes `Reserve` a bit
of a misnomer. Nomad is not expecting the device plugin to reserve the
device, but it's telling the device plugin that Nomad _has reserved_
the device, and to tell the client where it's been mounted.

Which leaves us in a tricky spot.

The device plugin can only get the state of the device via the
fingerprint, so unless there's a visible side-effect of the device
being used by a task, the plugin doesn't know when a task is done with
the device.

Well, I did warn you that this series would include mistakes and dead
ends. Unfortunately it looks like we're beyond the point of "without
hacks", so what are my options?

First, I could certainly "cheat" and try to get a change in the device
plugin behavior into Nomad itself. Perhaps the plugin should be sent a
notice that the device isn't needed? Or maybe the `Reserve` API should
have more information about the allocation? But that's the riskiest
approach because we're pretty serious about backwards compatibility in
Nomad's APIs, so we'd have to live with that change for a long
time. And besides, our team has plenty of more important work on their
plate than my silly experiments!

I could implement this whole workflow as a separate pre-start task
using a
[`lifecycle`](https://www.nomadproject.io/docs/job-specification/lifecycle)
block (this was suggested by
[@anapsix](https://twitter.com/anapsix/status/1358339913868079105) on
Twitter). We often recommend pre-start tasks because they make a great
"escape hatch" for Nomad feature requests that we're unsure if we want
to implement, or ones we just don't have the time for on the road
map. But in this case it doesn't meet the design requirement of having
a separate operator and job submitter persona. The pre-start task
would have to be privileged and that lets a job submitter execute
arbitrary code as root on the host.

A variant on that idea would be to implement a custom task driver that
_only_ exposes a dataset for other tasks in the allocation. This would
improve on the arbitrary pre-start task by having a [plugin
configuration](https://www.nomadproject.io/docs/configuration/plugin)
controlled by the operator. There are a few disadvantages to a task
driver: there would be extra running processes for each dataset, and
implementing a task driver is just a lot more work to implement. But a
task driver already has hooks for the task's lifecycle, so it would
let Nomad manage when the ZFS workflows happen.

Or I could implement a CSI plugin after all. I had wanted to steer
away from that because of how painful I'd found CSI plugins. But at
least I know in this case the CSI plugin will be well-behaved with
Nomad. Curses.

Lastly, just because the Nomad plugin API doesn't do what I want,
doesn't mean my device plugin client couldn't also communicate with
Nomad via its HTTP API. The plugin is already privileged code running
as Nomad's user (typically root), so it could make blocking queries to
the client to get allocation state on its own node.

Although weeks of coding can save hours of planning, I think I'm at
the point where it's time to do some small experiments to explore
these options. But next post I want to take a short detour to talk
about RFCs.
