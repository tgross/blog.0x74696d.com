---
categories:
- development
- nomad
- golang
date: 2021-02-15T12:00:00Z
title: "A ZFS Driver for Nomad, Part 2"
slug: zfs-driver-for-nomad-part2
---

A keen observer will note the title of this series has been
altered. In the previous post I discussed an option to have a device
driver that communicated with the Nomad API. Because device plugins
are launched via
[`go-plugin`](https://github.com/hashicorp/go-plugin), we don't
typically have to worry about securing their communication with
Nomad. But if the plugin were to talk to the Nomad HTTP API, we'd need
to give it ACL tokens and certificates for mTLS. This was going to
introduce a bunch of operational lifecycle complexity I don't want to
deal with.

This design exercise has certainly given me some interesting things to
think about for the future of Nomad's Device Plugin API. But it looks
like the best way to move forward is to implement the ZFS plugin as a
CSI driver. _Sigh_. Fine. Let's get to it.

If I take a look at the [CSI organization on
GitHub](https://github.com/container-storage-interface), there's a
notable lack of starter projects or examples. That's because the
developer community for CSI is working over in the [Kubernetes
CSI](https://github.com/kubernetes-csi) organization. There's not
exactly a skeleton project there either, but we do have the
[drivers](https://github.com/kubernetes-csi/drivers) repo which looks
promising at first. That includes a
[`csi-common`](https://github.com/kubernetes-csi/drivers/tree/master/pkg/csi-common)
package, but that was last updated 2 years ago. Most of this code
seems to have made its way over to the
[`csi-driver-host-path`](https://github.com/kubernetes-csi/csi-driver-host-path)
plugin repo, so that should serve as a good guide for the bits of the
spec that Kubernetes implements. There are also some reasonably solid
[developer
docs](https://kubernetes-csi.github.io/docs/developing.html).

I also did a quick survey of the landscape and found the
[`democratic-csi`](https://github.com/democratic-csi/democratic-csi)
project, which aims to be a framework for CSI plugins. But those folks
are writing plugins in NodeJS, so that's not going to help me. But,
hey, it's cool that they at least acknowledge
[Nomad](https://github.com/democratic-csi/democratic-csi/blob/master/docs/nomad.md).

Time to get to coding. I'll start by creating the repo in GitHub [^1],
including the MPL2 license and a golang `.gitignore` file. I clone
that down and run `go mod init github.com/tgross/zfs-csi-driver`. I
know we'll need the protobufs from the CSI spec library, and I know
from having worked on the orchestrator side that this is a gRPC
service, so I'll grab that while I'm at it:

```sh
require (
        github.com/container-storage-interface/spec v1.3.0
        google.golang.org/grpc v1.35.0
)
```

The CSI specification is broken into three gRPC services:
**Identity**, **Node**, and **Controller**. I'll dig into the Node and
Controller services in later posts, but all plugins need to run the
Identity service. Nomad will call the Identity service when the plugin
task starts and for liveness checks, and the plugin responds with
metadata and capabilities.

In CSI the plugin implements the "server" and the orchestrator (Nomad
or Kubernetes) is the client. So I'll start by implementing an empty
[`IdentityServer`
interface](https://github.com/container-storage-interface/spec/blob/v1.3.0/lib/go/csi/csi.pb.go#L5185-L5190):

```go
type IdentityServer struct{}

func (i *IdentityServer) GetPluginInfo(
	context.Context, *csipb.GetPluginInfoRequest) (
	*csipb.GetPluginInfoResponse, error) {
	return nil, nil
}

func (i *IdentityServer) GetPluginCapabilities(
	context.Context, *csipb.GetPluginCapabilitiesRequest) (
	*csipb.GetPluginCapabilitiesResponse, error) {
	return nil, nil
}

func (i *IdentityServer) Probe(context.Context, *csipb.ProbeRequest) (
	*csipb.ProbeResponse, error) {
	return nil, nil
}
```

I'm just dropping all this in `main.go` for the moment. As the series
goes on I'll factor each of the services out into their own files. For
now I just want to make sure I've got all the dependencies figured
out. I'll instantiate a unix socket listener with some very crude
argument parsing, and wire that up to an out-of-the-box gRPC
server. I'll run that, just making sure it compiles and that it binds
to the socket file. That's [31e0be5](https://github.com/tgross/zfs-csi-driver/commit/31e0be537de241fa1e76c793d016cb4e5afe8d94).

Next I'll take a quick detour to add the binary output to our
gitignore, and whip up a makefile. The `build` target is simple for
now but I always end up wanting to add a bunch of flags later. And I
add a `check` target to run some linting and static analysis. That's
[722669e](https://github.com/tgross/zfs-csi-driver/commit/722669e67095f8b30bc28af55439a3602e56a048):

```
$ make check
gofmt ......... ok!
go vet ........ ok!
staticcheck ... ok!
go mod tidy ... ok!
```

With our _mise_ solidly _en place_, I'll get the Identity service into
enough shape where I can at least make sure it'll register itself as a
CSI plugin. I'll have both the [Identity service
spec](https://github.com/container-storage-interface/spec/blob/master/spec.md#identity-service-rpc)
and the generated [library
docs](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi)
handy.

First I need to return a
[`GetPluginInfoResponse`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#GetPluginInfoResponse). I
don't think I have a use for the manifest field, but I'll leave that
commented out here to remind myself later.

```diff
+const (
+       pluginName    = "zfs.csi.0x74696d.com"
+       pluginVersion = "0.0.1"
+)
+
 type IdentityServer struct{}

 func (i *IdentityServer) GetPluginInfo(context.Context, *csipb.GetPluginInfoRequest) (
        *csipb.GetPluginInfoResponse, error) {
-       return nil, nil
+       return &csipb.GetPluginInfoResponse{
+               Name:          pluginName,
+               VendorVersion: pluginVersion,
+               // Manifest: map[string]string{}, // TODO?
+       }, nil
 }
```

Next is the
[`GetPluginCapabilitiesResponse`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#GetPluginCapabilitiesResponse). I'm
expecting that I'll want to implement the optional Controller service
and that I'll want to be able to tell Nomad not to provision onto
particular nodes. So I'll add both those capabilities to the
response. The constuctor for the `PluginCapability` is pretty gross,
but I've come to expect that from protobuf-generated code.

```diff
 func (i IdentityServer) GetPluginCapabilities(
        context.Context, *csipb.GetPluginCapabilitiesRequest) (
        *csipb.GetPluginCapabilitiesResponse, error) {
-       return nil, nil
+       return &csipb.GetPluginCapabilitiesResponse{
+               Capabilities: []*csipb.PluginCapability{
+                       {
+                               Type: &csipb.PluginCapability_Service_{
+                                       Service: &csipb.PluginCapability_Service{
+                                               Type: csipb.PluginCapability_Service_CONTROLLER_SERVICE,
+                                       },
+                               },
+                       },
+                       {
+                               Type: &csipb.PluginCapability_Service_{
+                                       Service: &csipb.PluginCapability_Service{
+                                               Type: csipb.PluginCapability_Service_VOLUME_ACCESSIBILITY_CONSTRAINTS,
+                                       },
+                               },
+                       },
+               },
+       }, nil
 }
```

And lastly is the
[`Probe`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#ProbeResponse)
RPC, which has the dubious distinction of not returning a simple bool
for the `Ready` field, but wrapping the type in some Google protobuf
library helper. So I had to add that to my imports.

```diff
 func (i *IdentityServer) Probe(context.Context, *csipb.ProbeRequest) (
        *csipb.ProbeResponse, error) {
-       return nil, nil
+       return &csipb.ProbeResponse{
+               Ready: &pbwrappers.BoolValue{Value: true},
+       }, nil
 }
```

That's it for now with the Identity service
([27e646e](https://github.com/tgross/zfs-csi-driver/commit/27e646eccb4eb63cb3bb148b8db97c1a4fad7589)). In
a later post I'll have these RPC endpoints fingerprint the plugin
environment to assert plugin health contingent on access to a
particular zpool, and that the plugin has whatever tools or libraries
it needs.

Now to verify this runs on Nomad. Normally for development I'd
probably prefer to run the plugin via the `raw_exec` or `exec` driver,
but a CSI plugin needs to be able to run with `CAP_SYSADMIN` so unless
and until we give the `exec` driver a much-needed refresh, I'll need
to use the `docker` or `podman` driver.

So that I don't have to constantly rebuild the Docker image, I'll
bind-mount the binary into a standard container. My first pass at this
used the `busybox` base image, but I was getting a perplexing "no such
file or directory". After burning a few minutes debugging my Docker
mount configuration, I realized why:

```
$ ldd bin/zfs-csi-driver
        linux-vdso.so.1 (0x00007fff1fc47000)
        libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f7e29b7e000)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f7e2978d000)
        /lib64/ld-linux-x86-64.so.2 (0x00007f7e29d9d000)
```

What gives? Doesn't go build statically-linked binaries? Yes, but if
you include any package that has C bindings, it'll be dynamically
linked by default. This includes `os/user` and the all-important `net`
package from the stdlib. So binding only the binary into the container
will only work if the container image includes these libraries. The
busybox base image is all statically linked, so there's no libc or
pthread to use. I could fix this with the `netgo` build tag [^2] or
`CGO_ENABLED=0` but there's a pretty good chance I'll want to link to
libzfs later anyways. Instead I'll swap out for the `debian:buster`
base image, which has the same libc and other libraries as my
development machine. That's
[46daf09](https://github.com/tgross/zfs-csi-driver/commit/46daf091a20c2c0eedc2459f3058a579f2a3a48c).

I fire up a Nomad dev agent and run the plugin job:

```
$ nomad plugin status csi-zfs
ID                   = csi-zfs
Provider             = zfs.csi.0x74696d.com
Version              = 0.0.1
Controllers Healthy  = 0
Controllers Expected = 1
Nodes Healthy        = 0
Nodes Expected       = 1

Allocations
No allocations placed
```

The plugin registers, but it's not being marked healthy. We can see
why in the Nomad client logs:

> 2021-02-15T15:47:33.838-0500 [WARN] client.csi-zfs: finished client
> unary call: grpc.code=Unimplemented duration=512.367µs
> grpc.service=csi.v1.Controller grpc.method=ControllerGetCapabilities
>
> 2021-02-15T15:47:33.839-0500 [WARN] client.csi-zfs: finished client
> unary call: grpc.code=Unimplemented duration=357.548µs
> grpc.service=csi.v1.Node grpc.method=NodeGetInfo

I haven't implemented the Controller and Node services yet! Next time,
I'll talk a bit more about the architecture of a CSI plugin, what
these services do, and hopefully get the plugin into a healthy status.


[^1]: Which I always forget proves to be annoying when they use the
    default email address for the initial commit, which is currently
    my work address. Although I suppose all this code is copyright my
    employer anyways.
[^2]: Passing `-tags netgo` forces go to use a pure-go implementation
    of `net` that doesn't use `getaddrinfo` or other libc functions,
    but if you're implementing a client rather than a server I'd
    recommend against this because it introduces some operational
    gotchas with DNS.
