---
categories:
- development
date: 2021-07-27T12:00:00Z
title: "Networking for a Firecracker Lab"
slug: networking-firecracker-lab
---

Several of my personal projects require creating and destroying a lot
of virtual machines, so I've started porting them over from QEMU to
[Firecracker](https://firecracker-microvm.github.io/) to speed up
development. I'm now at the point where I need to make some of these
VMs accessible from the internet and other machines on the LAN. My
scenario is that I have three physical machines (2 NUCs and my
development laptop) that act as virtual machine hosts. Some of them
are currently running services on QEMU virtual machines, which I
intend to migrate over to Firecracker eventually but I don't want a
flag day for migration.

The obvious question given that I was a
[Nomad](https://www.nomadproject.io/) maintainer is why I wouldn't use
a Nomad [Firecracker task
driver](https://github.com/cneira/firecracker-task-driver), but it
turns out I'm not running a Nomad cluster across these machines. The
NUCs are powered off most of the day; if I happen to need them I fire
a wake-on-LAN to boot them and wait for their services to come
up. Nomad's control plane doesn't tolerate having peers offline for
extended periods of time, so it's just the wrong use case for this
home lab.

[Radek Gruchalski](https://gruchalski.com/about/) has a great series
([I](https://gruchalski.com/posts/2021-02-06-taking-firecracker-for-a-spin/),
[II](https://gruchalski.com/posts/2021-02-07-vault-on-firecracker-with-cni-plugins-and-nomad/),
[III](https://gruchalski.com/posts/2021-02-17-bridging-the-firecracker-network-gap/))
where he explores Firecracker, tries it out with Nomad and CNI, and
gets bridge networking going after forking
[`firectl`](https://github.com/firecracker-microvm/firectl). Gruchalski's
approach builds on top of a
[post](https://jvns.ca/blog/2021/01/23/firecracker--start-a-vm-in-less-than-a-second/)
by the always-delightful Julia Evans
([@b0rk](https://twitter.com/b0rk)).

Evans configures the networking of the VM guests by passing boot
arguments (TIL! See also this section from the [RHEL networking
guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/networking_guide/sec-configuring_ip_networking_from_the_kernel_command_line)),
and creates the tuntap device in her script. Gruchalski instead uses
[Container Network Interface (CNI)](https://www.cni.dev/) plugins to
create a bridge network, assign an IP, and create the required tuntap
device via the
[`tc-redirect-tap`](https://github.com/awslabs/tc-redirect-tap)
plugin. Two areas where my requirements are different are the jailer
and persistent IP addressing.

Because I may end up with some VMs exposed to the internet, I want to
tighten up their isolation using the
[jailer](https://github.com/firecracker-microvm/firecracker/blob/main/docs/jailer.md). The
jailer runs in a network namespace and containerizes itself by
unsharing its PID namespace and running in a pivot root. (That's
right, it's a VM running in a container!)

I'd like for VM IPs to be persistent so that I can register DNS
entries for their services and set up any forwarding rules I need at
the router. These need to persist across reboots of the underlying
host.

So I built on top of Evans' and Gruchalski's approaches by adding
support for the jailer and ensuring that I can have persistent IP
addresses, and of course the extra bits that need to happen to make
these IPs routable on my LAN. I wrapped this all up in a control
script I'm calling
[`vmctl`](https://gist.github.com/tgross/8aa33b65cba1850ebe430f33fafd6e41)
which gets invoked as follows:

```sh
vmctl create --id $(uuidgen) --template ./vmconfigs/example.json
```

This creates a network namespace named after the `$id` and runs the
CNI plugins to allocate an IP address from the network bridge and
create a tuntap device. The output from CNI gets saved as a JSON file
to disk, so that if we run `vmctl create` again with the same `$id` we
can look for that file, skip creating the network, and reuse the same
IP address. Next `vmctl` creates a chroot containing the kernel and
root filesystem for the VM, and starts up the jailer. The jailer
isolates itself, drops privileges, and exec's into the Firecracker
process to boot the VM.

(Aside: `vmctl` is pronounced "vm-cuddle". Obviously.)

## Bridge Interface

I have an Ansible template that looks something like the following,
where `{{ prefix }}` gets rendered with a "subnet prefix" for each of
the three physical machines. For example, one machine's prefix is
`"192.168.30"`, which gets rendered as an IP of `192.168.30.1/24` with
an IP range of `192.168.30.2` to `192.168.30.254`:

```xml
<network>
  <name>default</name>
  <bridge name='virbr0' stp='on' delay='0'/>
  <forward mode='route'/>
  <ip address='{{ prefix }}.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='{{ prefix }}.2' end='{{ prefix }}.254'/>
    </dhcp>
  </ip>
</network>
```

A handler in the Ansible role configures this bridge as follows:

```sh
virsh net-define ./virbr0.xml
virsh net-autostart default
virsh net-start default
```

And that results in a bridge interface named `virbr0` with the IP
`192.168.30.1/24` on our example machine.

## CNI

Next I have a CNI configuration file in `/etc/cni/net.d`. When CNI
invokes this configuration, it creates the bridge if it doesn't exist
(although we've already created it for the QEMU VMs above). It then
allocates an IP address from the given range. Note that the range
starts at `192.168.30.32` so that I have some room at the bottom for
the existing QEMU VMs. Next it sets up the appropriate iptables
ingress rules, and creates a tuntap device.

```json
{
  "name": "firecracker",
  "cniVersion": "0.4.0",
  "plugins": [
    {
      "type": "bridge",
      "name": "firecracker-bridge",
      "bridge": "virbr0",
      "ipam": {
        "type": "host-local",
        "resolvConf": "/etc/resolv.conf",
        "dataDir": "/srv/vm/networks",
        "subnet": "192.168.30.0/24",
        "rangeStart": "192.168.30.32",
        "gateway": "192.168.30.1"
      }
    },
    {
      "type": "firewall"
    },
    {
      "type": "tc-redirect-tap"
    }
  ]
}
```

The CNI plugin is running as root inside the network namespace, before
we start the jailer. But the tuntap device will be opened by the
unprivileged Firecracker process the jailer starts. CNI plugin authors
understandably focus on the use case of K8s, so it took me a bit of
digging to figure out how to get the `tc-redirect-tap` plugin to
create a device accessible to the jailer user. There are undocumented
arguments to set the user ID, group ID, and tap name. The
[`cnitool`](https://www.cni.dev/docs/cnitool/) doesn't accept
arbitrary arguments for plugins but does accept a `CNI_ARGS`
environment variable. These arguments get passed to _every_ plugin in
a chain of plugins, so you need to pass another argument
`IgnoreUnknown=1` that by convention the plugin authors are supposed
to respect. The resulting `vmctl` code looks something like the
following (some error handling and setting the `$uid` and `$gid` of
the jailer user have been elided for brevity).


```sh
if [ ! -f "/var/run/netns/${id}" ]; then
    sudo ip netns add "$id"
fi

# I've named the device tap1 because the default is tap0
# and it makes it easier to verify args have been passed
# through to the CNI plugin correctly; we can reuse the
# name safely because each device ends up in its own netns
cniArgs="IgnoreUnknown=1"
cniArgs="${cniArgs};TC_REDIRECT_TAP_UID=$uid"
cniArgs="${cniArgs};TC_REDIRECT_TAP_GID=$gid"
cniArgs="${cniArgs};TC_REDIRECT_TAP_NAME=tap1"

result=$(sudo CNI_PATH="/opt/cni/bin" \
              NETCONFPATH="/etc/cni/net.d" \
              CNI_ARGS="$cniArgs" \
              cnitool add firecracker \
              "/var/run/netns/$id")

# we don't pipe the cnitool straight into the file because
# we want to return early if we get an error without writing
# this file that we use to check for idempotency
echo "$result" | sudo tee "/srv/vm/networks/${id}.json"
```

The `firecracker` argument to the `add` subcommand refers to the name
of the CNI configuration.

## Firecracker Configuration

The next step for `vmctl` is to create the chroot environment for the
jailer and to create a Firecracker configuration file from the
`$template` argument. A minimal template looks like the following JSON
file.

```json
{
  "boot-source": {
    "kernel_image_path": "vmlinux-5.8",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "alpine-rootfs.ext4"
    }
  ],
  "machine-config": {
    "vcpu_count": 1,
    "mem_size_mib": 512
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "$MAC",
      "host_dev_name": "$TAP"
    }
  ]
}
```

For the kernel, initrd, and any drives, `vmctl` looks for the file in
a well-known location, creates a hardlink from there to the
jailer's chroot, and ensures the target is owned by the jailer user
and group. In this example, `/srv/vm/kernels/vmlinux-5.8` will be
hardlinked to `/srv/vm/jailer/$id/root/vmlinux-5.8`.

The template file is rendered with the CNI configuration. We get the
MAC address, append an `ip` argument to the boot arguments, and do
some fairly gross things with `jq` to write that configuration to
`/srv/vm/configs/$id.json`. That configuration is hardlinked to the
chroot at `/srv/vm/jailer/$id/root/config.json` and owned by root.

```bash
# read from the CNI ouput
netcfg="/srv/vm/networks/${id}.json"
ip=$(jq -r '.ips[0].address | rtrimstr("/24")' < "$netcfg")
gateway_ip=$(jq -r '.ips[0].gateway' < "$netcfg")
mac=$(jq -r '.interfaces[] | select(.name == "eth0").mac' < "$netcfg")
mask="255.255.255.0"

# shorten the uuid to something reasonable
hostname=$(echo "$id" | tr -d '-' | head -c 16)

# capture the args from the template
boot_args=$(jq -r '."boot-source".boot-args' < "$template")

# append our ip configuration:
# guest-ip:[server-ip]:gateway-ip:netmask:hostname:iface:state
boot_args="${boot_args} ip=${ip}::${gateway_ip}:${mask}:${hostname}:eth0:off"

# render the template
jq "(.\"boot-source\".boot_args) |= \"$boot_args\"
    | (.\"network-interfaces\"[0].guest_mac) |= \"$mac\"
      " < "$template" | \
          sudo tee "/srv/vm/config/${id}.json"
```

Lastly `vmctl` ties this all together by invoking jailer like I've
shown below. To get the `firecracker` binary I need to use `readlink`
so that I can chase a symlink from `/usr/local/bin` to my local build
from source.

```bash
sudo jailer \
     --id "$id" \
     --daemonize \
     --exec-file $(readlink $(which firecracker)) \
     --uid "$uid" \
     --gid "$gid" \
     --chroot-base-dir "/srv/vm/jailer" \
     --netns "/var/run/netns/$id" \
     --new-pid-ns \
     -- \
     --config-file "config.json"
```

## Stopping a VM

To stop one of the VMs without destroying it entirely, I need to send
it a graceful shutdown, and then clean up the runtime files in the
jailer's chroot. The next time I create the VM, `vmctl` will see that
we already have the network, VM configuration, and hardlinks in place
and will skip to calling jailer.

```sh
jail="/srv/vm/jailer/firecracker/${id}/root"
pid=$(sudo cat "${jail}/firecracker.pid")

sudo curl \
     --unix-socket \
     "${jail}/run/firecracker.socket" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -X PUT "http://localhost/actions" \
     -d "{ \"action_type\": \"SendCtrlAltDel\" }"

while :
do
    ps "$pid" > /dev/null || break
    sleep 1
    echo -n "."
done

echo
sudo rm -r "${jail}/firecracker.pid"
sudo rm -r "${jail}/dev"
sudo rm -r "${jail}/run"
sudo rm -r "${jail}/firecracker"
```

This doesn't currently handle cleaning up if the VM shuts itself down,
so I'll need to return to that at some point and also add a `vmctl
stop` for all running VMs to the host machine's shutdown.

## Routing

Finally, we need to set up routing so that packets from the host or
other machines can reach the VMs. On each host we set forwarding,
which looks like the following Ansible tasks but you can also do via
ex. `echo 1 > /proc/sys/net/ipv4/ip_forward`

```yml
- sysctl:
    name: net.ipv4.ip_forward
    value: '1'
    state: present
    reload: yes
  become: true

- sysctl:
    name: net.ipv4.conf.all.forwarding
    value: '1'
    state: present
    reload: yes
  become: true

- sysctl:
    name: net.ipv6.conf.all.forwarding
    value: '1'
    state: present
    reload: yes
  become: true
```

And then on the ISP's router, we set up routing rules. I've got a Fios
router here, so I go to the `#/advanced/routing` page and configure a
rule for each machine. The "destination" field is the subnet prefix
(ex. `192.168.30.0`), whereas the "gateway" field is the IP address of
the physical host for that subnet (ex. `192.168.1.101` for my laptop).

Now any machine on the LAN can reach any other machine on the LAN,
physical or virtual. And I can further configure port mapping in the
router to expose any of the machines to the public internet.
