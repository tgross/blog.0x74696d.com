---
categories:
- development
- nomad
- golang
date: 2021-02-21T08:00:00Z
title: "A ZFS Driver for Nomad, Part 3"
slug: zfs-driver-for-nomad-part3
---

Last time we implemented the Container Storage Interface (CSI)
**Identity** service, so now it's time to look at the **Controller** and
**Node** services. The CSI spec has a lot of detail as to the
protocol, but leaves a lot of the intentions behind each service left
unsaid for the implementer to discover.

The spec tells us that
[Node](https://github.com/container-storage-interface/spec/blob/master/spec.md#node-service-rpc)
service RPCs shall run on the node where the volume is used. There are
only a few required RPCs: `NodeGetCapabilities` that tells us which
RPCs are implemented, and `NodePublishVolume` and
`NodeUnpublishVolume` that are call when the orchestrator has a
workload that wants to use the volume. The `NodeStageVolume` and
`NodeUnstageVolume` are optional, and are for preparing the volume for
its first use on the node where the volume is used. These definitions
are pretty vague, but that's required for the CSI authors to cover a
very broad range of storage providers.

The optional
[Controller](https://github.com/container-storage-interface/spec/blob/master/spec.md#controller-service-rpc)
service RPCs include `CreateVolume`, `ControllerPublishVolume`, and
`CreateSnapshot`, so at first glance this sounds like I'll want this
for the ZFS plugin. But the Controller RPCs differ in one important
respect: they don't necessarily happen on the same node where we're
going to use the volume! Unfortunately the [Kubernetes CSI development
guide](https://kubernetes-csi.github.io/docs/developing.html) doesn't
describe the purpose of the Controller, but we can piece it together
from the requirements of its component RPCs.

The Controller service is for workflows with the storage provider
infrastructure APIs, whereas the Node service is for workflows
specific to a given host. If we use AWS Elastic Block Storage (EBS)
volumes as an example, the Controller service tells AWS to create the
EBS volume (`CreateVolume`) and attach the volume to the EC2 virtual
machine (`ControllerPublishVolume`), whereas the Node service formats
the volume (`NodeStageVolume`) and mounts it for the container
(`NodePublishVolume`).

In the case of the ZFS plugin, there's no "remote ZFS API". I'll
ultimately need some sort of service to store the snapshots that I
`zfs send`, but all the workflows for this will need to be driven from
the host where the volume is in use. So I can drop the Controller
service entirely.

With that in mind, I want to get the plugin to the point where it
registers as healthy with Nomad. The last error we got was because
the `NodeGetInfo` service wasn't implemented:

> 2021-02-15T15:47:33.839-0500 [WARN] client.csi-zfs: finished client
> unary call: grpc.code=Unimplemented duration=357.548µs
> grpc.service=csi.v1.Node grpc.method=NodeGetInfo

First, I'll do a bit of refactoring and move the Identity service into
its own file. I can remove the controller capability from
`GetPluginCapabilities`, and I can change out the "monolith" for
"node" in my jobspec for the plugin. Next I'll implement the
[`NodeServer`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#NodeServer)
interface, just by dropping a bunch of empty function bodies in a new
`node.go` file. All that is commit
[b77e1fe](https://github.com/tgross/zfs-csi-driver/commit/b77e1fe20cb5e58411bcc09a28d87a81815a4aee).

I compile and run that, but still get the same error. So I check the
allocation logs and find the following:

> ERROR: 2021/02/21 18:17:22 [core] grpc: server failed to encode
> response: rpc error: code = Internal desc = grpc: error while
> marshaling: proto: Marshal called with nil

Let's look at the spec for
[`NodeGetInfo`](https://github.com/container-storage-interface/spec/blob/master/spec.md#nodegetinfo)
and the
[`NodeGetInfoResponse`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#NodeGetInfoResponse)
in a little more detail.

The fields look oriented towards cloud storage use cases, where cloud
vendor storage volumes will be attached to cloud vendor VMs over cloud
vendor networks. We can see this comment for the `node_id` field:

```go
// The identifier of the node as understood by the SP.
// This field is REQUIRED.
// This field MUST contain enough information to uniquely identify
// this specific node vs all other nodes supported by this plugin.
// This field SHALL be used by the CO in subsequent calls, including
// `ControllerPublishVolume`, to refer to this node.
// The SP is NOT responsible for global uniqueness of node_id across
// multiple SPs.
```

Well using the hostname probably isn't a great option here. I'll let
the operator set this value, assuming they'll want to use the Nomad
node ID via [attribute
interpolation](https://www.nomadproject.io/docs/runtime/interpolation).

For the `max_volumes_per_node` field, I see:

```go
// Maximum number of volumes that controller can publish to the node.
```

Curious.[^1] Well, we have no controller. So I can skip this.

The `Topology` works out to be a map of strings. We could have these
automatically pick up values from the environment Nomad provides, but
in the interest of portability, I'll have the user provide these as a
list of `--topology` flags. I'm building up enough config now that
I'll pull that out into its own struct, file, and a `newConfig`
function that hides it away from us. That commit is
[128b936](https://github.com/tgross/zfs-csi-driver/commit/128b9365a53725be346dd84cd28bae79e82fc7ec).

But wait a sec... what's this comment at the top of [`NodeGetInfo`](https://github.com/container-storage-interface/spec/blob/master/spec.md#nodegetinfo)?

> A Node Plugin MUST implement this RPC call if the plugin has
> `PUBLISH_UNPUBLISH_VOLUME` controller capability.

We _don't_ have that capability, as we removed it earlier. So that RPC
shouldn't be getting hit. It's a bug in Nomad! When the Nomad client
fingerprints the plugin, it checks `NodeGetInfo` if
[`p.fingerprintNode`](https://github.com/hashicorp/nomad/blob/v1.0.3/client/pluginmanager/csimanager/fingerprint.go#L110-L111)
is set, which is set if the plugin is of type
[`PluginCSITypeNode`](https://github.com/hashicorp/nomad/blob/v1.0.3/client/pluginmanager/csimanager/instance.go#L58). That
check for `NodeGetInfo` should be for `p.fingerprintController`, not
`p.fingerprintNode`. Oops! I'll take a quick detour to open
[nomad/#10055](https://github.com/hashicorp/nomad/issues/10055), but
in the meantime we'll keep our implementation in place and we can rip
it out once that's been fixed in Nomad.

With `NodeGetInfo` implemented, I compile and run on Nomad again. I
see the client starts it with all the arguments I'd expect, but now I
get an error for `NodeGetCapabilities`:

> 2021-02-21T14:15:28.181-0500 [WARN] client.csi-zfs: finished client
> unary call: grpc.code=Internal duration=2.401155ms
> grpc.service=csi.v1.Node grpc.method=NodeGetCapabilities

Armed with the
[`NodeGetCapabilities`](https://github.com/container-storage-interface/spec/blob/master/spec.md#nodegetcapabilities)
spec and the
[`NodeGetCapabilitiesResponse`](https://pkg.go.dev/github.com/container-storage-interface/spec@v1.3.0/lib/go/csi#NodeGetCapabilitiesResponse)
doc, I can work up an empty response body:

```diff
 func (n *NodeServer) NodeGetCapabilities(context.Context, *csipb.NodeGetCapabilitiesRequest) (
        *csipb.NodeGetCapabilitiesResponse, error) {
-       return nil, nil
+       return &csipb.NodeGetCapabilitiesResponse{}, nil
 }
```

That silences the error:

> 2021-02-21T14:20:21.541-0500 [DEBUG] client: detected new CSI plugin: name=csi-zfs type=csi-node
>
> 2021-02-21T14:20:21.543-0500 [DEBUG] client.csi-zfs: volume manager setup complete


But this endpoint is what advertises the plugins capabilities, so I'll
return the capabilities instead:

```diff
 func (n *NodeServer) NodeGetCapabilities(context.Context, *csipb.NodeGetCapabilitiesRequest) (
        *csipb.NodeGetCapabilitiesResponse, error) {
-       return nil, nil
+
+       return &csipb.NodeGetCapabilitiesResponse{
+               Capabilities: []*csipb.NodeServiceCapability{
+                       {
+                               Type: &csipb.NodeServiceCapability_Rpc{
+                                       Rpc: &csipb.NodeServiceCapability_RPC{
+                                               Type: csipb.NodeServiceCapability_RPC_STAGE_UNSTAGE_VOLUME,
+                                       },
+                               },
+                       },
+               },
+       }, nil
 }
```

If I build and run the new plugin, it registers itself and is marked
as healthy by the Nomad server, ready to publish volumes. That's
commit
[02ef228](https://github.com/tgross/zfs-csi-driver/commit/02ef228886042f3f524d2a8429829b15bd94f53e).


```text
$ nomad plugin status csi-zfs
ID                   = csi-zfs
Provider             = zfs.csi.0x74696d.com
Version              = 0.0.1
Controllers Healthy  = 0
Controllers Expected = 0
Nodes Healthy        = 1
Nodes Expected       = 1

Allocations
ID        Node ID   Task Group  Version  Desired  Status   Created  Modified
f73abbe3  9c559244  plugin      0        run      running  16s ago  4s ago
```

Once I get into performing ZFS workflows, I'm going to want to observe
them. So one last item before I wrap up today's work is to add some
logging. I'm fond of the API for
[`apex/log`](https://pkg.go.dev/github.com/apex/log), so I'll configure a
logger in `config.go`.

```diff
+       var logLevel = flag.String("log-level", "debug", `Logging level. One of:
+debug, info, warn, error, fatal`)

        flag.Parse()

+       log.SetLevelFromString(*logLevel)
+       log.SetHandler(jsonlog.Default)
+
        return config{
                socketPath: *sockPath,
                nodeID:     *nodeID,
```

And then thread that through the RPC servers.


```diff
 type NodeServer struct {
-       NodeID   string
-       Topology map[string]string
+       nodeID   string
+       topology map[string]string
+       log      *log.Entry
+}
+
+func NewNodeServer(nodeID string, topology map[string]string) *NodeServer {
+       return &NodeServer{
+               nodeID:   nodeID,
+               topology: topology,
+               log:      log.WithFields(log.Fields{"service": "Node"}),
+       }
 }
```

The resulting structured logs look like the following when I do `nomad
alloc logs -stderr :alloc_id`. I'm not wild about the timing traces
being at `INFO` but I can live with it. That's committed as
[6b0de82](https://github.com/tgross/zfs-csi-driver/commit/6b0de82c0dde3ded8b310b97b3bb5ca7267fc3b3).

> {"fields":{"duration":0},"level":"info","timestamp":"2021-02-21T20:58:58.462860527Z","message":"GetPluginCapabilities"}

Next time, I'll finally start making some ZFS datasets!

[^1]: If you find yourself saying this, stop and check what you're
    doing. As we'll discover in a moment.
