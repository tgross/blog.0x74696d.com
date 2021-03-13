---
categories:
- development
- nomad
- golang
date: 2021-03-13T08:00:00Z
title: "A ZFS Driver for Nomad, Part 4"
slug: zfs-driver-for-nomad-part4
---

It's time to start talking to ZFS, so the first decision I need to
make it whether I want to use a binding to `libzfs` or wrap the
command line tools. There's a `libzfs-core` library that's intended to
be the stable interface to ZFS, but I wasn't able to find a golang
binding to it and didn't feel like writing my own. These leaves us
with two main options:

* [mistifyio/go-zfs](https://github.com/mistifyio/go-zfs), which wraps
  the ZFS CLI.
* [bicomsystems/go-libzfs](https://github.com/bicomsystems/go-libzfs),
  which wraps the unstable `libzfs`.

Both are permissively licensed. The `go-libzfs` library has a fork by
Canonical at [ubuntu/go-libzfs](https://github.com/ubuntu/go-libzfs),
and both seem active which is good news. So first I did a quick spike
with `go-libzfs`, which as we'll see below turned out to be the right
move.

For the final code listing of the spike see [this
gist](https://gist.github.com/tgross/bac0fe124015afec4f68d19a167a6be0). In
my first pass at building this, I ran into this mysterious error:

```
$ go build -o zfsspike
# github.com/bicomsystems/go-libzfs
../go-libzfs/zpool.go:1108:39: could not determine kind of name for C.pool_initialize_func_t
../go-libzfs/zpool.go:1108:5: could not determine kind of name for C.zpool_initialize
```

And that's the point at which I realized that I need bindings to a
specific version of `libzfs`. In my environment I'm not on the
bleeding edge either.

```
$ dpkg -l libzfslinux-dev
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                        Version            Architecture       Description
+++-===========================-==================-==================-============================================================
ii  libzfslinux-dev             0.7.5-1ubuntu16.10 amd64              OpenZFS filesystem development files for Linux
```

Fortunately, unlike `mistifyio/go-zfs`, the `go-libzfs` library has
tags for different versions of ZFS. The tags don't match the version
of `libzfs` you might have, so there's a bit of experimentation to
find the right version. In my case, I ended up with
[v.0.2.3-5](https://pkg.go.dev/github.com/bicomsystems/go-libzfs@v0.2.3-5).

```
$ go build -o zfsspike && sudo ./zfsspike -name test1
Created zfs dataset rpool/home/tim/test1
         size => "1614445176"
         free => "lz4"
    [prop 47] => "0"
    [prop 63] => "26624"
         name => "volume"
       health => "57344"
    [prop 44] => "all"
    [prop 58] => "standard"
...
etc.
```

That works, buts adds a new complication to our development cycle: we
need to make sure that the container has access to the appropriate
libraries:

```
$ ldd zfsspike
        linux-vdso.so.1 (0x00007ffc741fe000)
        libzfs.so.2 => /lib/libzfs.so.2 (0x00007ff2551b9000)
        libzpool.so.2 => /lib/libzpool.so.2 (0x00007ff254c3c000)
        libnvpair.so.1 => /lib/libnvpair.so.1 (0x00007ff254a29000)
        libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007ff25480a000)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007ff254419000)
        libzfs_core.so.1 => /lib/libzfs_core.so.1 (0x00007ff254214000)
        libuutil.so.1 => /lib/libuutil.so.1 (0x00007ff254002000)
        libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007ff253c64000)
        libblkid.so.1 => /lib/x86_64-linux-gnu/libblkid.so.1 (0x00007ff253a17000)
        libz.so.1 => /lib/x86_64-linux-gnu/libz.so.1 (0x00007ff2537fa000)
        librt.so.1 => /lib/x86_64-linux-gnu/librt.so.1 (0x00007ff2535f2000)
        libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007ff2533ee000)
        /lib64/ld-linux-x86-64.so.2 (0x00007ff255401000)
        libuuid.so.1 => /lib/x86_64-linux-gnu/libuuid.so.1 (0x00007ff2531e7000)
```

The Debian Buster container image I was using doesn't have a `libzfs`
package at all, and Stretch only has 0.6.5, whereas I've got 0.7.x on
my machine. So I'll start from the same Ubuntu base as my target:

```Dockerfile
FROM ubuntu:bionic
RUN apt-get update && apt-get install -y libzfslinux-dev
COPY zfsspike /bin/zfsspike
```

After building that image I can test it and get the same results. At
some point I'll probably want to have a process to release separate
container images for separate versions of `libzfs`, and I certainly
don't want to haul around all of Ubuntu if I don't have to. We'll put
a pin in that for later. Our spike has proved the concept, so now to
wire this all up in the CSI plugin.

```
$ docker run -it --privileged --rm test:latest /bin/zfsspike -name test1
Created zfs dataset rpool/home/tim/test1
     failmode => "4096"
    [prop 49] => "0"
    [prop 53] => "latency"
    [prop 68] => "18446744073709551615"
    cachefile => "10485760"
   expandsize => "off"
    [prop 63] => "26624"
...
```

Because I like to work clean, I'll first remove the configuration that
supports the `NodeGetInfo` RPC. We discovered last time that's really
only there to support controllers. The `NodeGetInfo` RPC can return a
mostly empty body to make Nomad happy, and I can get rid of the
topology flags. That's commit
[a594409](https://github.com/tgross/zfs-csi-driver/commit/a594409117d61a2cd6aa43d325db181673c168af).

The Node RPCs map 1:1 to some specific operations in ZFS, so I'll
define an interface and implement an empty body for it. Then I'll want
to call this from the Node RPCs. Remember that `NodeStageVolume`
happens when the node first gets the volume, and the
`NodePublishVolume` is called when a workload wants to mount it.

```go
type ZFS interface {
    Create(*ZFSCreateOptions) error
    Mount(*ZFSMountOptions) error
    Unmount(*ZFSUnmountOptions) error
    Destroy(*ZFSDestroyOptions) error
}
```

I'm using an interface here because creating and destroying datasets
requires root privileges and modifies the host environment. So if I
want to ever test the rest of the code, I'll want to be able to swap
that out for a side-effect free mock. Also, at some point I'll want
the ZFS client to be able to perform a bunch of other operations that
don't map to Node RPCs, so having the RPC code depend on a smaller
slice of interface reduces the size of whatever test mocks I'll need.

That's all committed as
[de75651](https://github.com/tgross/zfs-csi-driver/commit/de756510ecc8af168329e80616bb323c7fa61cc0).

Next I want to start creating datasets, but I need to figure out how
to configure all the parameters. There's going to be 3 sources of
configuration for every mounted dataset:

* Configuration we set for the plugin. This could be passed as
  configuration flags or a config file for the plugin. The cluster
  operator is the one who sets these configs.
* Configuration we set when registering the volume as part of the
  `VolumeContext`. These values could come from either the cluster
  operator or the job submitter, if they have `write-volume` too.
* Configuration we set when mounting the volume. This is set on a
  per-job basis, so should be limited to those options that can change
  between mounts.

I don't want job submitters to control the root dataset path or the
maximum size (quota) of a dataset, and I'll probably want to provide a
configurable default quota. So I'll wire up configuration for those
values and provide some basic validation that the root ZFS dataset
exists. That's
[f4bdf44](https://github.com/tgross/zfs-csi-driver/commit/f4bdf44d9709ccc12f6a71c03311cb0458041564)

Next I'm going to look at what parameters the
[`NodeStageVolume`](https://github.com/container-storage-interface/spec/blob/master/spec.md#nodestagevolume)
and
[`NodePublishVolume`](https://github.com/container-storage-interface/spec/blob/master/spec.md#nodepublishvolume)
RPCs are going to give me.

For `NodeStageVolume` I've got a volume ID and a staging path
controlled by the orchestrator. This staging path is where it should
be mounted during staging but we can safely ignore that for ZFS where
we can stage without mounting. The publish context field is only used
if there's a controller, so I can safely ignore that. Secrets are of
no use here either.

The volume capability is a little hairy to unpack: it has a bunch of
structs with empty bodies currently used as flags (presumably because
the spec authors expect to fill them out in the future). So I'll have
to nil-check those. I'm planning on only exposing ZFS `filesystem`
datasets and not `volume`, so I'll validate that the request isn't
asking for a raw block volume. And don't want to let the user set the
a filesystem type, because it's always ZFS.

But I also want to let the user pass mount flags. These will show up
as a slice of strings. The volume context is a map of properties that
the orchestrator will pass to the mount step from when the volume was
created. In Nomad we've differentiated between creating the volume and
registering it, which allows us to set all the creation parameters
even for plugins that don't support the Controller's `CreateVolume`
RPC. So I want to pass the parameters that we recorded during volume
registration as a map to the plugin. I'll use these to set the
per-volume quota and any other option that can't be changed after the
dataset is created. They should override any mount flags. I'll parse
these fields from the request and add it to the create options struct.

For `NodePublishVolume` I have most of the same fields, with the extra
quirk of the "read only" field and a target path, which is what we
really care about for making available for the workload. And lastly
for the `NodeUnpublishVolume` and `NodeUnstageVolume` RPCs there's
just the name and path to deal with.

I don't want the ZFS client to have to worry about serialization
concerns, so I'll do some basic validation of the inputs and ditch the
protobuffers in the RPC handlers before passing down options into the
ZFS client. This is all committed as
[5cf96ac](https://github.com/tgross/zfs-csi-driver/commit/5cf96ace406a0684492a88420acf497da62487c0)

Now that I've got those parameters, how do I pass them to the ZFS
client?

ZFS supports _lots_ of properties (see
[`zfsprops(8)`](https://openzfs.github.io/openzfs-docs/man/8/zfsprops.8.html)). These
get passed as a map to the
[`DatasetCreate`](https://pkg.go.dev/github.com/bicomsystems/go-libzfs#DatasetCreate)
function, but they're typed a little unexpectedly:

```go
props := make(map[zfs.Prop]zfs.Property)
props[zfs.DatasetPropVolsize] = zfs.Property{Value: strSize}
```

The library doesn't have a set of string constants that map to the
properties, because this is wrapping `libzfs` and not the command line
tools. Unfortunately although they have a
[`DatasetPropertyToName`](https://pkg.go.dev/github.com/bicomsystems/go-libzfs#DatasetPropertyToName)
function they don't have the reverse. You can create whatever mapping
you'd like and the library "resolves" them into the real
properties. This turns out to make debugging during development a
little challenging if you've got a lot of properties; if the property
doesn't successfully resolve it won't have a name you can
`fmt.Printf`, just a number to look up. In any case, there'll be a bit
of code to map the inputs to those properties.

On top of that, I don't want the user to be able to set properties
that are read-only to the operator, like "mounted", so I'll need to
filter all those out.

First I'll sketch out a `Create` method that gives me an idea of the shape of the API:

```go
func (z *ZFSClient) Create(opts *ZFSCreateOptions) error {
    dcPath := z.path(opts.Name)
    props, err := z.createProperties(opts.StagingPath, opts.Params, opts.MountFlags)
    if err != nil {
        return fmt.Errorf("validation error: %v", err)
    }

    d, err := zfs.DatasetCreate(dcPath, zfs.DatasetTypeFilesystem, props)
    if err != nil {
        return err
    }
    d.Close()
    return nil
}

func (z *ZFSClient) createProperties(
    stagingPath string, params map[string]string, mountFlags []string) (
    map[zfs.Prop]zfs.Property, error) {

    props := map[zfs.Prop]zfs.Property{}
    return props, nil
}
```

So I know I'll most likely end up with a giant switch statement that
validates the parameters and merges them on top of the plugin
defaults. So far almost everything in the code has been "plumbing":
serializing and deserializing, shuffling protobufs around, setting up
config, etc. Nothing worth writing unit tests for. But now that I've
got some logic to worry about, I'll start writing some tests. Note
that for unit testing, I don't want to have real ZFS datasets created,
so I need to keep the validation logic cleanly factored away from the
side-effects.

I start with a failing test like this:

```go
func TestZFS_CreateProperties(t *testing.T) {
    zclient := testZFSClient(t.Name())
    require.NotNil(t, zclient)

    testCases := []struct {
        desc        string
        params      map[string]string
        mountFlags  []string
        expected    map[zfs.Prop]zfs.Property
        expectedErr error
    }{
        {
            desc: "quota parameter overrides default",
            params: map[string]string{
                "quota": "30M",
            },
            mountFlags: []string{},
            expected: map[zfs.Prop]zfs.Property{
                zfs.DatasetPropQuota: zfs.Property{Value: "30M"},
            },
            expectedErr: nil,
        },
    }

    for _, tc := range testCases {
        tc := tc
        t.Run(tc.desc, func(t *testing.T) {
            t.Parallel()

            props, err := zclient.createProperties(tc.desc, tc.params, tc.mountFlags)
            if tc.expectedErr != nil {
                require.EqualError(t, err, tc.expectedErr.Error())
            } else {
                require.NoError(t, err)
                require.EqualValues(t, tc.expected, props)
            }
        }
    }
}
```

In my first attempt I tried to generate a string-to-ZFS properties
function to reverse `DatasetPropertyToName`, only to realize the pool
properties and dataset properties were implemented as the same set,
but without distinct names. This resulted in a big old switch
statement with duplicate keys, so I had to toss that and just
hand-roll a function for the properties I care about.

There's a crapton of code here for parsing the configuration,
parameters, etc. Once I've got most of this, it becomes obvious that
the `Create` isn't going to use the `mountFlags`, so I toss those out
and keep them only for the `Mount` method that gets called from the
`NodePublishVolume` RPC.

Then I got a little stuck when looking at [this
method](https://pkg.go.dev/github.com/bicomsystems/go-libzfs@v0.2.3-5#Dataset.Mount):

```go
func (d *Dataset) Mount(options string, flags int) (err error)
```

The flags aren't documented in `go-libzfs`, so I had to do a little
spelunking in the ZFS source code. The
[`mount.h`](https://github.com/openzfs/zfs/blob/zfs-0.7.5/lib/libspl/include/sys/mount.h#L89)
header file defines them. Later versions of this code add encryption
flags, but I can't test those on the environment where I'm working so
I'm going to leave these out for now.

All that mess is commit
[3ab18f1](https://github.com/tgross/zfs-csi-driver/commit/3ab18f1691b988829803f66781efa9af26714158).

At this point I decide I want to run that build on Nomad so I can do
some testing with it. We saw earlier that we needed a new base to work
with. That's
[e1dca20](https://github.com/tgross/zfs-csi-driver/commit/e1dca208753fe90d863143b33ddb0ecdcd43000e)
for now, but I'd like to revisit that with a leaner container image
later on.

Unfortunately the development cycle of spinning up Nomad, running the
plugin, registering the volume, and deploying a job that wants that
volume is a little longer than I'd like. So I ended up temporarily
hacking in a testing flag option like the one below (in
`main.go`). That's not committed but I'll want to come back to revisit
it for integration testing later:

```go
if cfg.testing {
    err := zclient.Create(&ZFSCreateOptions{
        Name:        "test-volume-0",
        StagingPath: "/csi/staging/test-volume[0]/rw-file-system-single-node-writer",
        MountFlags:  []string{"readonly", "-O"},
        Params:      nil,
    })
    if err != nil {
        fmt.Println(err)
    }
    return
}
```

After a bit of testing I find some bugs. There are some default properties that weren't compatible with my environment. And I forgot to defer closing the dataset in the `Mount`, `Unmount`, and `Destroy` methods. Those fixes are [84cc719](https://github.com/tgross/zfs-csi-driver/commit/84cc719d5a6a3f6a3d207fbe6f5d88411065e116)

At this point I was ready to work up an example job for consuming the
volume to test the plugin end-to-end. That's when I realized the
plugin job specification wasn't marked with `privileged = true`, even
though I was the one to write the giant warning about that on the
Nomad
[`csi_plugin`](https://www.nomadproject.io/docs/job-specification/csi_plugin#csi_plugin-parameters)
parameters documentation. How embarrassing! That's in
[f0fd028](https://github.com/tgross/zfs-csi-driver/commit/f0fd028663ec382826e527543f5516a7ee2f08a2)

At this point I get the following error when Nomad's CSI hook tries to mount the volume:

> 2021-03-13T13:30:55-05:00  Driver Failure   failed to create container: API error (400): invalid mount config for type "bind": bind source path does not exist: /tmp/NomadClient194408044/csi/node/csi-zfs/per-alloc/b7995d2d-5afc-bcf3-d171-e23767ccaeff/test-volume[0]/rw-file-system-single-node-writer


This path looks ridiculous but it breaks down to
`${nomad_data_dir}/csi/node/${plugin_id}/per-alloc/${alloc_id}/${volume_id}/${mount_type}`. If
I add some
[`go-spew`](https://pkg.go.dev/github.com/davecgh/go-spew/spew)
debugging, I see the following in the plugin's allocation logs:

```
$ nomad alloc logs 1fd
(*main.ZFSMountOptions)(0xc00010fe00)({
 Name: (string) (len=13) "test-volume-0",
 StagingPath: (string) (len=61) "/csi/staging/test-volume[0]/rw-file-system-single-node-writer",
 TargetPath: (string) (len=100) "/csi/per-alloc/fa664bfb-30a5-3104-9999-b6defe5e1c41/test-volume[0]/rw-file-system-single-node-writer",
 MountFlags: ([]string) (len=2 cap=2) {
  (string) (len=8) "readonly",
  (string) (len=2) "-O"
 },
 Params: (map[string]string) <nil>
})
```

That made me realize we hadn't yet made the target path the dataset's
mount point, so that's done in
[654140a](https://github.com/tgross/zfs-csi-driver/commit/654140a5f7914be78ebd670db9055a0a2584e42f). Now
when I test the example job, I can see the dataset get created:

```
$ zfs list | grep test-volume
rpool/home/tim/test-volume-0                                                               96K   355G    96K  /csi/per-alloc/ca4c08e7-eaab-5ebd-6582-1ef254a39b77/test-volume[0]/rw-file-system-single-node-writer
```

If I exec into the job's allocation and write to the location in the
`volume_mount`, I can take a ZFS snapshot of it, clone that snapshot,
and verify that the dataset had been properly mounted to the
container:

```
$ nomad alloc exec ca4 /bin/sh
/ # touch /srv/test.txt
/ # exit

$ sudo zfs snapshot rpool/home/tim/test-volume-0@test1
$ sudo zfs clone rpool/home/tim/test-volume-0@test1  rpool/home/tim/restored
$ ls ~/restored
test.txt
```

At this point if I try to stop the job, I'll get the following error
in the Nomad client logs:

> 2021-03-13T13:50:30.474-0500 [ERROR] client.alloc_runner: postrun
> failed: alloc_id=ca4c08e7-eaab-5ebd-6582-1ef254a39b77 error="hook
> "csi_hook" failed: 1 error occurred: rpc error: could not detach
> from node: node detach volume: rpc error: code = Unknown desc =
> Cannot destroy dataset rpool/home/tim/test-volume-0: filesystem has
> children

That's because the dataset has child datasets because of my
snapshot. I'll have to clean that up manually for the moment, but
that'll be something to figure out when I implement the snapshot
workflow.

```
$ sudo zfs destroy rpool/home/tim/test-volume-0
cannot destroy 'rpool/home/tim/test-volume-0': filesystem has children
use '-r' to destroy the following datasets:
rpool/home/tim/test-volume-0@test1
$ sudo zfs destroy -r rpool/home/tim/test-volume-0
```

At this point the plugin can create, mount, unmount, and delete ZFS
datasets. But right now we're destroying every dataset as soon as
we're done with it! And we haven't yet touched upon migrating the
datasets between nodes. In the next post in this series, I'll work
through a design for coordinating the plugins for peer-to-peer backup
and migration of data.
