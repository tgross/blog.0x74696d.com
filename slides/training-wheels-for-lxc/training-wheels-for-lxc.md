# Docker: Training Wheels for LXC

<div style="position: absolute; bottom: 0">
<p>tim gross | @0x74696d</p>
<p>http://0x74696d.com/slides/training-wheels-for-lxc/slides.html</p>
</div>

# Presenter Notes

- I'm Tim Gross
- I the DevOps lead and I build software infrastructure for DramaFever.
- slides, code, more details in an upcoming blog post

---

# What Does Docker Actually Do?

---

# The core: LXC

- chroot + backing filesystem
- cgroups
- network namespace
- PID namespace
- UID namespace
- IPC namespace
- utsname namespace

# Presenter Notes

- isolate file system
- control privileges, constrain resource use
- containers can have their own hostname
- namespace ex: init in container is PID1 but not on the host

---

# AUFS: Another Unioning File System

<img alt="AUFS" style="margin-left:100px;margin-top:100px" src="./images/docker-aufs.png">

# Presenter Notes

- AUFS has a limitation in the number of layers you can have (42)
- managing disk space on small root volumes gets to be a pain in resource-constrained environments like AWS instances
- No good tooling for understanding relationships of AUFS layer dependencies

---

# Docker container management

<img alt="Docker Overview" style="margin-left:100px" height=625 src="./images/docker_overview.png">

# Presenter Notes

- 1. ask for image from repo
- 2. copy images to container and configure
- 3. start application w/ chroot and dropped privs
- 4. provides a bridge
- 5. configures NAT

---

# How's Docker Work?

---

# Docker images

Docker images are each an AUFS layer

    !shell-session
    root@docker:~# docker images
    REPOSITORY         TAG      ID            CREATED     SIZE
    example.com/nginx  latest   3b3e56c8728b  2 days ago  194.2 kB (virtual 486.3 MB)
    140218             latest   9fcdcd1b466a  2 days ago  809.3 kB (virtual 1.298 GB)
    <none>             <none>   f5e0aaf7c1c6  2 days ago  804.8 kB (virtual 1.298 GB)
    <none>             <none>   5b54b1c18491  3 days ago  782.5 kB (virtual 1.298 GB)
    <none>             <none>   3d141a007dde  3 days ago  573.9 kB (virtual 1.298 GB)
    <none>             <none>   42a27ea66c7b  3 days ago  490.2 kB (virtual 1.298 GB)
    ...


# Presenter Notes

- docker images management tool
- list of source repository, tag, id (guid)
- note no relationship shown between images (<none> images effectively abandoned in the UI)

---

# Docker images

What are Docker images on-disk?

    !shell-session
    root@docker:/var/lib/docker/graph# ls -gGh
    total 528K
    drwxr-xr-x 3 4.0K Feb 10 22:12 01643fd18047352d9a79eb75b7e308a1d008d554c56a71021c8c55d05f6f6711
    drwxr-xr-x 3 4.0K Feb 11 21:37 05f332145eb39853a9a7bc4c8b998534db817ae9a912d63a4308d7512a38e988
    drwxr-xr-x 3 4.0K Feb 10 22:12 07b820fd749309f50ca4a768ca787891e5e3cd2b579784fd551a5db172cc17ab
    drwxr-xr-x 3 4.0K Feb 10 22:12 07ed199d2cc37d2cc14ff8fcb309f411c6fae4de0d54327980f69f603976b931
    drwxr-xr-x 3 4.0K Feb 10 21:55 083fef0ebd7d6fd80b73372b3f912b4ed1c7f41f3fbc799db03121b8b1e7b927
    drwxr-xr-x 3 4.0K Feb 10 21:55 08b0b462ef5b5bf3a10ac18163799f1946e2927630fda827a9de8e701e8077c0
    drwxr-xr-x 3 4.0K Feb 10 21:55 09ff3f834fa8c309d7bab71db296d1ff7a85a342a3cd20a83ae97acf8c676765
    drwxr-xr-x 3 4.0K Feb 10 21:55 0e0e364a43825c51cc0b944e9003926ac75b42bf32955f2c5b7830762dc89021
    drwxr-xr-x 3 4.0K Feb 10 21:55 0f0fcfa72154076edff2af62852cd58bb194f25702b86cc9897b3debcf63777c
    drwxr-xr-x 3 4.0K Feb 10 21:55 10114b1b7dcc0684e226e5182df2a23c1517b5b3ca7ec1bd47320a654f2d2052
    ...


# Presenter Notes

- note the long filenames (from this point forward we'll show ... to make them fit on slides)

---

# Docker images

What's inside an image?

    !shell-session
    root@docker:/var/lib/docker/graph/01643fd18047352...# ls -gGh
    total 12K
    -rw------- 1 1.2K Feb 10 21:57 json
    drwxr-xr-x 8 4.0K Dec 20 19:22 layer
    -rw------- 1    6 Feb 10 22:12 layersize

    root@docker:/var/lib/docker/graph/01643fd18047352...# ls -gGh layer/
    total 12K
    drwxr-xr-x 2 4.0K Dec 20 19:22 dev
    drwxr-xr-x 4 4.0K Dec 20 19:22 etc
    drwxr-xr-x 3 4.0K Dec 20 19:22 var


# Presenter Notes

- Metadata about the layer
- A layer contains the difference between this layer and the layer below
- Note: no easy way from here to tell the relationships from here

---

# Docker containers

Containers (running and stopped)

    !shell-session
    root@docker:~# docker ps -a
    ID              IMAGE                      COMMAND           CREATED       STATUS      PORTS
    2167ea158044    140218:latest              /etc/init/django  5 hours ago   Up 5 hours
    92fa573ac642    example.com/nginx:latest   /etc/init/nginx   2 days ago    Up 2 days   443->443, 80->80
    2e826a369057    11f4582baf48               /etc/init/nginx   2 days ago    Exit 137
    1c92b2165cbb    11f4582baf48               /etc/init/nginx   2 days ago    Exit 137
    2b74a9181b27    11f4582baf48               /bin/bash         2 days ago    Exit 0

    root@docker:/var/lib/docker/containers# ls -gGh
    total 104K
    drwx------ 3 4.0K Feb 14 16:15 0c21a529abee4324a3b38ac3d1c455dfd93f6afc60bb9ce04153694180f238aa
    drwx------ 3 4.0K Feb 14 14:23 0db4dffbc35475bb998284eb72269056d7848c420be2f220614f77ffc7d6fd47
    drwx------ 3 4.0K Feb 13 20:39 10a8dd1bc774467dc41b7ee46a6b015d041a9709995ae6a9a57b4199d3325f98
    drwx------ 3 4.0K Feb 14 14:20 137208649445ebb77f80ad6fa13300d49d74fcf2a67a612c30f3e6d6cc375b8e
    drwx------ 3 4.0K Feb 13 20:39 14a4ab0cfdc5a9934cff5b6b3b6912df3aca4620131d7927ec5cccf77de606cf
    drwx------ 3 4.0K Feb 14 16:15 15b9a4212c83f93972ed79710da737eb5cf3afbe8e74cc6342366c80ef77ab6a
    drwx------ 4 4.0K Feb 14 16:11 1b881777ccbeb3a76031201f3bf8a713325ccd3b4677bc6dd38a3f30c2484b47
    drwx------ 3 4.0K Feb 14 18:43 1c92b2165cbbf5fcb7d36a9c8c5a247f32f3058f369e3d4a76a64bf77bded198
    ...

---

# Docker containers

What's in Docker containers?

    !shell-session
    root@docker:/var/lib/docker/containers/0c21a529abee...# ls -gGh
    total 364K
    -rw------- 1  341K Feb 14 16:15 0c21a529abee...-json.log
    -rw-r--r-- 1   991 Feb 14 16:15 config.json
    -rw-r--r-- 1  3.5K Feb 14 16:11 config.lxc
    -rw-r--r-- 1    50 Feb 14 16:11 hostconfig.json
    drwxr-xr-x 60 4.0K Feb 14 16:11 rootfs
    -rw------- 1     0 Feb 14 16:11 rootfs.hold
    drwxr-xr-x 7  4.0K Feb 14 16:11 rw

    root@docker:/var/lib/docker/containers/0c21a529abee...# ls -gGh rw/
    total 12K
    drwxr-xr-x 2 4.0K Feb 14 16:11 dev
    drwxr-xr-x 3 4.0K Aug 30 22:31 usr
    drwxr-xr-x 4 4.0K Feb 11 16:01 var
    -r--r--r-- 1    0 Feb 14 16:11 .wh..wh.aufs
    drwx------ 2 4.0K Feb 14 16:11 .wh..wh.orph
    drwx------ 2 4.0K Feb 14 16:11 .wh..wh.plnk


# Presenter Notes

- inside the container is the same diffs from the image, plus runtime changes
- note rootfs only exists in root containers (?)
- in theory you could chroot into the rw directory, but finding the right container/layer for a given file would be scary
- note the config.lxc file, will be important later

---

# Docker networking

LXC creates `iptables` rules, Docker adds NAT

    !shell-session
    root@docker:/var/lib/docker/volumes# iptables -t nat -nL
    Chain PREROUTING (policy ACCEPT)
    target     prot opt source            destination
    DOCKER     all  --  0.0.0.0/0         0.0.0.0/0        ADDRTYPE match dst-type LOCAL

    Chain INPUT (policy ACCEPT)
    target     prot opt source            destination

    Chain OUTPUT (policy ACCEPT)
    target     prot opt source            destination
    DOCKER     all  --  0.0.0.0/0         !127.0.0.0/8     ADDRTYPE match dst-type LOCAL

    Chain POSTROUTING (policy ACCEPT)
    target     prot opt source            destination
    MASQUERADE  all  --  172.17.0.0/16    !172.17.0.0/16

    Chain DOCKER (2 references)
    target     prot opt source            destination
    DNAT       tcp  --  0.0.0.0/0         0.0.0.0/0        tcp dpt:8000 to:172.17.0.9:8000
    DNAT       tcp  --  0.0.0.0/0         0.0.0.0/0        tcp dpt:80 to:172.17.0.25:80
    DNAT       tcp  --  0.0.0.0/0         0.0.0.0/0        tcp dpt:443 to:172.17.0.25:443


# Presenter Notes

- does post-routing to let containers talk to the outside world (LXC does this)
- sets up NAT rules to let inbound requests get routed to the containers with exposed ports (Docker does this)

---

# Docker CLI

- docker run => lxc-start (plus generate lxc.config)
- docker attach => lxc-console
- docker rm => lxc-destroy
- docker commit + docker push => lxc-snapshot (sort of)
- ??? => lxc-suspend

# Presenter Notes

- most of the docker commands are wrappers on LXC commands
- docker run: copies on-disk image to new container, chroots
- docker commit: an anonying feature of Docker is finding the real file; without AUFS you can just go to the directory, chroot, and edit-in-place. no commit process needed.

---

# docker run

After `docker run -d example.com/nginx /etc/init/nginx`

    !shell-session
    root@docker:~# ps afx
    ...
     5186 ?        Sl     3:14  \_ /usr/bin/docker -D -d
    10832 ?        S      0:00      \_ lxc-start -n 92fa573ac6422... -f /v
    10836 ?        S      0:00          \_ /bin/bash /etc/init/nginx
    10869 ?        S      0:00              \_ nginx: master process nginx
    10878 ?        Sl     0:14                  \_ nginx: worker process
    10879 ?        Sl     0:14                  \_ nginx: worker process
    10880 ?        Sl     0:12                  \_ nginx: worker process
    10881 ?        Sl     0:14                  \_ nginx: worker process
    ...

---

# see docker run

Docker forks an lxc-start command

    !shell-session
    lxc-start \
        -n 92fa573ac642... \
        -f /var/lib/docker/containers/92fa573ac642.../config.lxc \
        -- /.dockerinit \
           -g 172.17.42.1 \
           -e HOME=/ \
           -e PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
           -e container=lxc \
           -e HOSTNAME=92fa573ac642 \
           -- /etc/init/nginx

    root@docker:~# lxc-start --usage
    Usage: lxc-start [-d|--daemon] [-f|--rcfile=RCFILE] [-s|--define=DEFINE] [-c|--console=CONSOLE]
           [-C|--close-all-fds] [-n|--name=NAME] [-h|--help] [--usage]
           [-q|--quiet] [-o|--logfile=LOGFILE] [-l|--logpriority=LOGPRIORITY]


# Presenter Notes

- all we're doing it executing lxc-start with option flags and a startup script
- there's that config.lxc script we saw earlier

---

# run, docker, run.

- lxc-clone the image to a new container
- generate a new LXC configuration file
  - attach shared volumes
  - assign IP address
  - common LXC configs
- lxc-start the container with a `.dockerinit` file

# Presenter Notes

- we can do this ourselves, right?

---

# Why roll our own?

- So we can understand and control the abstraction
- Make different choices than DotCloud/Docker with respect to AUFS, cgroups, etc.
- Docker daemon and repo are redundant and increase our attack surface

---

# Go away or I will replace you with a very small shell script

---

# lxc.config

The Docker `lxc.config` file is the same config file we would create with LXC without Docker!

    !bash
    # hostname
    lxc.utsname = 3358b5c54e13

    # network configuration
    lxc.network.type = veth
    lxc.network.flags = up
    lxc.network.link = docker0
    lxc.network.name = eth0
    lxc.network.mtu = 1500
    lxc.network.ipv4 = 172.17.0.18/16

    # root filesystem
    lxc.rootfs = /var/lib/docker/containers/3358b5c54e13.../rootfs

# Presenter Notes

- Hostname set by truncating giant GUID
- Docker sets an IP, LXC uses dnsmasq by default
- Create a rootfs (giant GUID again) where the container will chroot

---

# lxc.config

LXC config determines what pty/tty get exposed

    !bash
    # use a dedicated pts for the container (and limit the number of
    # pseudo terminal available)
    lxc.pts = 1024

    # disable the main console
    lxc.console = none

    # no controlling tty at all
    lxc.tty = 1

# Presenter Notes

- maybe we don't want to disable the console?

---

# lxc.config

LXC config determines what devices we allow access to

    !bash
    # no implicit access to devices
    lxc.cgroup.devices.deny = a

    # /dev/null and zero
    lxc.cgroup.devices.allow = c 1:3 rwm
    lxc.cgroup.devices.allow = c 1:5 rwm

    # consoles
    lxc.cgroup.devices.allow = c 5:1 rwm
    lxc.cgroup.devices.allow = c 5:0 rwm
    lxc.cgroup.devices.allow = c 4:0 rwm
    lxc.cgroup.devices.allow = c 4:1 rwm

    # /dev/urandom,/dev/random
    lxc.cgroup.devices.allow = c 1:9 rwm
    lxc.cgroup.devices.allow = c 1:8 rwm

    ...

# Presenter Notes

- also /dev/pts, tuntap, fuse, rtc

---

# lxc.config

After `docker run -d -v /var/log/nginx:/var/log example.com/nginx /etc/init/nginx`

    !bash
    lxc.mount.entry = proc /var/lib/docker/containers/3358b5c54e13.../rootfs/proc proc nosuid,nodev,noexec 0 0
    lxc.mount.entry = sysfs /var/lib/docker/containers/3358b5c54e13.../rootfs/sys sysfs nosuid,nodev,noexec 0 0
    lxc.mount.entry = devpts /var/lib/docker/containers/3358b5c54e13.../rootfs/dev/pts devpts newinstance,ptmxmode=0666,nosuid,noexec 0 0
    lxc.mount.entry = shm /var/lib/docker/containers/3358b5c54e13.../rootfs/dev/shm tmpfs size=65536k,nosuid,nodev,noexec 0 0

    # Inject docker-init
    lxc.mount.entry = /usr/bin/docker /var/lib/docker/containers/3358b5c54e13.../rootfs/.dockerinit none bind,ro 0 0

    # In order to get a working DNS environment, mount bind (ro) the host's /etc/resolv.conf into the container
    lxc.mount.entry = /etc/resolv.conf /var/lib/docker/containers/3358b5c54e13.../rootfs/etc/resolv.conf none bind,ro 0 0

    # This is from our -v flag
    lxc.mount.entry = /var/log/nginx /var/lib/docker/containers/3358b5c54e13.../rootfs//var/log none bind,rw 0 0

# Presenter Notes

- bind-mount locations from host to container guest
- .dockerinit sets environment variables in container that we set with -e flag in `docker run`
- note that Docker -v always sets (rw) and not (ro); we can do anything we want here
- LXC config file also drops a few privileges for container (cgroups)

---

# LXC template

LXC templates generate the config file and generate the initial file system

    !shell-session
    root@lxc:~# ls -gGh /usr/lib/lxc/templates/
    total 88K
    -rwxr-xr-x 1 8.1K Oct 29 22:16 lxc-busybox
    -rwxr-xr-x 1 9.6K Oct 29 22:16 lxc-debian
    -rwxr-xr-x 1  11K Oct 29 22:16 lxc-fedora
    -rwxr-xr-x 1 8.9K Oct 29 22:16 lxc-opensuse
    -rwxr-xr-x 1 5.0K Oct 29 22:16 lxc-sshd
    -rwxr-xr-x 1  20K Oct 29 22:16 lxc-ubuntu
    -rwxr-xr-x 1  11K Oct 29 22:16 lxc-ubuntu-cloud

# Presenter Notes

- template != disk image
- just bash scripts that download to the rootfs
- also typ. generate lxc config file, /etc/network/interfaces, /etc/hosts, /etc/hostname, etc.

---

# `notdocker`

---

# Our goals

Creating new containers

1. Start with a template
2. Configure container
3. Install application/configs
4. Commit to repository on S3

Starting a container

1. Download the container on S3 if it doesn't exist on-disk.
2. Run the application
3. Mount volumes and expose ports as needed

# Presenter Notes

- this is just one potential deployment scenario
- the point of this is that we can change any of these elements when we roll out own.
- better yet would be using your favorite config mgmt too (Puppet, Saltstack, Ansible, etc)
- another approach we could take here is to build our own LXC template script
- available at http://0x74696d.com/_code/training_wheels/notdocker, let's take a look

---

# `notdocker` results

After: `notdocker build -n test0 -p 80:80 -f setup.sh`

    !shell-session
    root@lxc:~# ls -gGh /var/lib/lxc/test0/
    total 12K
    -rw-r--r--  1 1.3K Feb 18 20:08 config
    -rw-r--r--  1  110 Feb 18 20:08 fstab
    drwxr-xr-x 23 4.0K Feb 18 20:08 rootfs

    root@lxc:~# head /var/lib/lxc/test0/config
    lxc.network.type=veth
    lxc.network.link=lxcbr0
    lxc.network.flags=up
    lxc.network.hwaddr = 00:16:3e:c4:76:e4
    lxc.utsname = test0

    lxc.tty = 4
    lxc.pts = 1024
    lxc.rootfs = /var/lib/lxc/test0/rootfs
    lxc.mount  = /var/lib/lxc/test0/fstab

# Presenter Notes

- in this case our setup just installs Nginx
- note that the container directory is easy to find

---

# `notdocker` results

The rootfs of the container is easy to browse and we could chroot to this directory to modify it.

    !shell-session
    root@lxc:~# ls -gGh /var/lib/lxc/test0/rootfs/
    total 84K
    drwxr-xr-x  2 4.0K Jan 30 07:06 bin
    drwxr-xr-x  3 4.0K Jan 30 07:06 boot
    drwxr-xr-x  4 4.0K Jan 30 07:05 dev
    drwxr-xr-x 86 4.0K Feb 18 20:08 etc
    drwxr-xr-x  3 4.0K Jan 30 07:06 home
    lrwxrwxrwx  1   33 Jan 30 07:05 initrd.img -> /boot/initrd.img-3.2.0-58-virtual
    drwxr-xr-x 18 4.0K Jan 30 07:05 lib
    drwxr-xr-x  2 4.0K Jan 30 07:04 lib64
    drwx------  2 4.0K Jan 30 07:06 lost+found
    drwxr-xr-x  2 4.0K Jan 30 07:04 media
    drwxr-xr-x  2 4.0K Apr 19  2012 mnt
    drwxr-xr-x  2 4.0K Jan 30 07:04 opt
    drwxr-xr-x  2 4.0K Apr 19  2012 proc
    drwx------  2 4.0K Jan 30 07:06 root
    drwxr-xr-x  2 4.0K Jan 30 07:06 run
    drwxr-xr-x  2 4.0K Jan 30 07:06 sbin
    drwxr-xr-x  2 4.0K Mar  5  2012 selinux
    drwxr-xr-x  2 4.0K Jan 30 07:04 srv
    drwxr-xr-x  2 4.0K Apr 14  2012 sys
    drwxrwxrwt  2 4.0K Jan 30 07:06 tmp
    drwxr-xr-x 10 4.0K Jan 30 07:04 usr
    drwxr-xr-x 12 4.0K Jan 30 07:06 var
    lrwxrwxrwx  1   29 Jan 30 07:05 vmlinuz -> boot/vmlinuz-3.2.0-58-virtual


---

# Inside the LXC container

After: `notdocker run -d -n test0 -- /etc/init/nginx`

We can use lxc-console to examine the container from the inside.

    !shell-session
    root@test0:~# netstat -antp
    Active Internet connections (servers and established)
    Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
    tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      3095/nginx
    tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      361/sshd
    tcp        0      0 10.0.3.133:49062        91.189.91.14:80         TIME_WAIT   -
    tcp6       0      0 :::22                   :::*                    LISTEN      361/sshd

---

# PID isolation

Inside the container:

    !shell-session
    root@test0:~# ps afx
      PID TTY      STAT   TIME COMMAND
        1 ?        Ss     0:00 /sbin/init
     3077 ?        Ss     0:00  \_ /bin/sh -e /proc/self/fd/9
     3095 ?        Ss     0:00      \_ nginx: master process /usr/sbin/nginx
     3096 ?        S      0:00         \_ nginx: worker process
     3097 ?        S      0:00         \_ nginx: worker process

Outside the container:

    !shell-session
    root@lxc:~# ps afx
     PID TTY      STAT   TIME COMMAND
    3084 ?        Ss     0:00 lxc-start -d -n test0
    3090 ?        Ss     0:00  \_ /sbin/init
    3196 ?        Ss     0:00  \_ /bin/sh -e /proc/self/fd/9
    6214 ?        Ss     0:00      \_ nginx: master process /usr/sbin/nginx
    6215 ?        S      0:00          \_ nginx: worker process
    6216 ?        S      0:00          \_ nginx: worker process

# Presenter notes

- aside: our /etc/init/nginx is just an upstart config

---

# When to Use LXC Over Docker?

- If managing AUFS is more painful than it's worth
- If you want to use btrfs snapshots or LVM for the backing store
- If your application dependencies are relatively fixed
- If you want to share read-only volumes between containers
- If your build process wants to write directly to the rootdir

# Presenter Notes

- in theory Docker is going to be more robust than your shell scrip (at Docker 1.0?
- remember: Docker is a generalized solution originally designed for PaaS, not for your app

---

# Docker: Training Wheels for LXC

<div style="position: absolute; bottom: 0">
<p>tim gross | @0x74696d</p>
<p>http://0x74696d.com/slides/training-wheels-for-lxc/slides.html</p>
</div>
