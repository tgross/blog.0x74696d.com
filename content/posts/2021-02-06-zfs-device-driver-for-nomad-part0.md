---
categories:
- development
- nomad
- golang
date: 2021-02-06T12:00:00Z
title: "A ZFS Device Driver for Nomad, Part 0"
slug: zfs-device-driver-for-nomad-part0
---

I've been the primary maintainer of Nomad's various storage
implementations since this past summer when the last other person
who'd worked on it left HashiCorp. That includes host volumes and the
Container Storage Interface (CSI), both of which were originally
designed by someone smarter than me.

But CSI is a bit of a mess in terms of providing any actual
abstraction. The spec focuses almost entirely on the protobuf
plumbing, several plugins don't comply with the specified concurrency
requirements or otherwise have Kubernetes-specific quirks, and half
the implementation in Kubernetes is out-of-tree or simply
unimplemented. That leads to things like plugins having implementation
bug in interfaces that no one has ever tested until Nomad came along
and tried it, and the plugin authors don't really care to fix it.

Arguably the notion of having a storage abstraction that abstracts
both the storage provider and the container orchestrator is ill
conceived from the get-go. Operators aren't running multiple
orchestrators and dozens of storage implementations; they're typically
going to be responsible for one orchestrator and at most two or three
semantically-incompatible storage providers (ex. a block storage, an
object storage, and maybe a network file system). The interfaces are
rightfully the storage vendor's or orchestrator developer's problem,
not yours as an end user. Instead we've dropped a steaming pile of
operational gotchas on your plate. So CSI is the sort of thing that
you'd try to make a standard if you were a giant tech company with a
history of pushing half-baked standards on the rest of the industry
for purposes of cementing your market dominance. Hypothetically
speaking, of course.

All that to say when I wanted to have a way to provide ZFS datasets to
a Nomad workload, I definitely didn't want to implement a CSI storage
provider for it. I have to deal with CSI during my day job. Yes, Nomad
is also my day job. Point taken.

Most of my little experiments get worked on in private, but the scope
of this is small and relevant to my employment so I thought I'd share
my process as I go. With only an hour or two here and there to spend,
I'm still hoping that this will take no more than a couple
weeks. Despite having been on the Nomad team for a while now, I
haven't had to dig into the device plugin system much. So expect
plenty of exploration, dead ends, rework, and plain old mistakes.

Let's start with a design. At HashiCorp or Joyent this would be an RFC
(Request For Comments) doc. While I don't need that level of formality
here, it's worth having the outline of a story for what I'm trying to
do up front.

Nomad has two primary user personas: the cluster operator and the job
submitter. In small orgs these will be the same people, but typically
the cluster operators are the folks responsible for the underlying
platform and have root on the Nomad hosts, whereas the job submitter
will have the rights to submit jobs to Nomad and varied levels of
access to debug them when things go wrong.

When I submit a job, I want to expose a ZFS dataset to my workload. I
want that ZFS dataset to be backed up. And when my workload gets
rescheduled I want the ZFS dataset to be available wherever the
workload is placed. Immediately this brings to mind ZFS snapshots and
ZFS send / receive. The existing
[`migrate`](https://www.nomadproject.io/docs/job-specification/migrate)
feature in Nomad doesn't have any hooks for plugins, so I'll probably
have to implement much of the ZFS send and receive workflow from
scratch.

Putting on my operator hat, I want all datasets a job submitter can
create to be children of a particular dataset given to Nomad. Of
course I'll also want disk quotas.

The best fit for these requirements is a [device
plugin](https://www.nomadproject.io/docs/internals/plugins/devices),
as I want to be able to mount data to arbitrary workloads, and not
create a new workload type as I would with a driver plugin. Not many
device plugins have been written; there's the baked-in Nvidia GPU
plugin, a fun hack for an [ePaper device
plugin](https://github.com/cgbaker/nomad-device-raspberry-epaper-hat)
by my colleague [Chris Baker](https://github.com/cgbaker), and a [USB
storage
plugin](https://gitlab.com/CarbonCollins/nomad-usb-device-plugin)
developed by Steven Collins out in the Nomad community. That's about
it. So I'm going to assume I'll hit some sharp edges to workaround or
that might need patches in Nomad proper if they're useful for other
authors.

The plugin needs to talk to ZFS. The hacky way to do this would be to
shell-out to the ZFS command line utilities. One advantage of this
would be that I can use the existence of the command line utilities as
part of our fingerprint, and I know those utilities will be compatible
whatever ZFS is on the host. That also makes packaging nicer. On the
other hand, it's awfully brittle to parse the command line output for
tools the plugin doesn't own, especially in the case of Nomad which is
running as a service and not interactively. So that's a detail to
figure out.

The Nomad device plugin API I need to implement has just three
methods: `Fingerprint`, `Stats`, and `Reserve`. Nomad will fingerprint
the device plugin to ask for the set of [available
devices](https://pkg.go.dev/github.com/hashicorp/nomad@v1.0.3/plugins/device#FingerprintResponse). This
happens on client startup and then again periodically. The device
plugin is expected to provide
[stats](https://pkg.go.dev/github.com/hashicorp/nomad@v1.0.3/plugins/device#DeviceStats)
for the devices it manages. And Nomad wants to send a list of device
IDs to reserve, expecting the plugin to return a
[reservation](https://pkg.go.dev/github.com/hashicorp/nomad@v1.0.3/plugins/device#ContainerReservation)
object with the set of devices and mounts. Immediately I see our first
challenge: the API expects a known set of device IDs, whereas our
design wants the job submitter to be able to define datasets on the
fly. Is this project dead on arrival? That would be embarrassing!

Next time, I'll look at the Nomad scheduler and see if I can come up
with a reasonable approach to handling the device ID.
