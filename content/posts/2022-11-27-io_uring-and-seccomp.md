---
categories:
- development
- security
date: 2022-11-27T12:00:00Z
title: "io_uring and seccomp"
slug: iouring-and-seccomp
---

Recent Linux kernels have the kqueue-alike [`io_uring`][] interface for
asynchronous I/O. Instead of making read and write syscalls, you write
batches of I/O requests to a circular buffer in userland called the
submission queue, and make a `io_uring_enter` syscall to submit them
to the kernel. Instead of making individual syscalls, `io_uring`
submission queue entries (SQEs) take an opcode for the specific I/O
operation they're performing, and that's mapped to the same kernel
code that normally services the syscall. You can read the results off
another buffer called the completion queue without making additional
syscalls to the kernel. This can meaningfully improve I/O performance,
especially in the face of Spectre/Meltdown mitigations.

A side effect is that `io_uring` effectively bypasses the protections
provided by seccomp filtering &mdash; we can't filter out syscalls we
never make! This isn't a security vulnerability per se, but something
you should keep in mind if you have especially paranoid seccomp
rules. Practically speaking it's going to be rare that anything I/O
related is going to be seccomp filtered, but I thought it was
interesting enough to reproduce myself.

Suppose we want to prevent our application from making outbound
network requests by blocking the `connect(2)` syscall. This is a
contrived example as you'd most likely implement this via network
namespaces or iptables. But let's imagine the application needs to
look up an upstream address and connect to it once, but we want to
ensure the application can never make any new connections after that.

<aside>Addendum 2022/11/28: Giovanni Campagna pointed out <a
href="https://mastodon.social/@gcampax/109417842749003392">on
Mastodon</a> that systemd uses seccomp filtering for its
RestrictAddressFamilies option. This controls the <code>socket</code>
syscall. But <code>socket</code> isn't one of the supported opcodes,
so io_uring applications still need to call the real
<code>socket</code> syscall and RestrictAddressFamilies works just
fine. Of course you can't call <code>connect</code> if you don't have
a socket in the first place, so that makes this example even more
contrived!</aside>

The examples below will stand-in for a buggy or compromised
application that's trying to make an outbound connection we want to
stop. First we'll use normal syscalls.

```rust
use std::env;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};

fn main() {
    let args: Vec<_> = env::args().collect();

    if args.len() <= 1 {
        panic!("no addr specified");
    }

    let socket_addr: SocketAddr = args[1].parse().unwrap();

    let mut stream = TcpStream::connect(socket_addr).unwrap();
    let mut buf = [0; 128];

    let result = stream.write(&mut buf);
    println!("written: {}", result.unwrap());

    let read = stream.read(&mut buf).unwrap();
    println!("read: {:?}", &buf[..read]);
}
```

In another terminal I'll run `netcat` listening on port 8000, and the
run this code to connect to it.

```
$ ./target/debug/no_iouring 127.0.0.1:8000
written: 128
read: [102, 111, 111, 10]
```

If we run this under `strace`, we'll see something like this among the
syscalls:

```
connect(3, {sa_family=AF_INET, sin_port=htons(8000), sin_addr=inet_addr("127.0.0.1")}, 16) = 0
```

Now let's look at the `io_uring` approach for the same code. Note this
example is directly copied from the `tokio-uring` [TCP stream
example][] code.

```rust
use std::{env, net::SocketAddr};
use tokio_uring::net::TcpStream;

fn main() {
    let args: Vec<_> = env::args().collect();

    if args.len() <= 1 {
        panic!("no addr specified");
    }

    let socket_addr: SocketAddr = args[1].parse().unwrap();

    tokio_uring::start(async {
        let stream = TcpStream::connect(socket_addr).await.unwrap();
        let buf = vec![1u8; 128];

        let (result, buf) = stream.write(buf).await;
        println!("written: {}", result.unwrap());

        let (result, buf) = stream.read(buf).await;
        let read = result.unwrap();
        println!("read: {:?}", &buf[..read]);
    });
}
```

If we run this under `strace`, we'll never see a `connect`
syscall. Instead we'll see a `io_uring_setup` to initialize the
buffers and then a series of syscalls like the following:

```
io_uring_enter(6, 1, 0, 0, NULL, 128)   = 1
```

Now let's add a seccomp filter. First we'll need to lookup the syscall
number from the Linux source:

```
$ grep connect ~/src/linux/arch/x86/entry/syscalls/syscall_64.tbl
42      common  connect                 sys_connect
```

Then using the [`seccomp` crate][] we'll create a rule that blocks all
uses of the syscall. Specifically the comparison function here is
saying that we'll block the syscall if the first argument (the file
handle) is greater than zero. We'll add this same code to the top of
the main function in both examples:

```diff
+extern crate libc;
+extern crate seccomp;
+
 use std::{env, net::SocketAddr};
+
+use seccomp::*;
 use tokio_uring::net::TcpStream;

 fn main() {
+    let mut ctx = Context::default(Action::Allow).unwrap();
+    let rule = Rule::new(
+        42, /* connect on x86_64 */
+        Compare::arg(0).using(Op::Gt).with(0).build().unwrap(),
+        Action::Errno(libc::EPERM), /* return EPERM */
+    );
+    ctx.add_rule(rule).unwrap();
+    ctx.load().unwrap();
+
     let args: Vec<_> = env::args().collect();

     if args.len() <= 1 {
```

If we run the synchronous syscall version, we'll get a permission
denied error:

```
$ ./target/debug/no_iouring 127.0.0.1:8000
thread 'main' panicked at 'called `Result::unwrap()` on an `Err` value:
Os { code: 1, kind: PermissionDenied, message: "Operation not permitted" },
src/bin/no_iouring.rs:28:54
note: run with `RUST_BACKTRACE=1` environment variable to display
a backtrace
```

Whereas if we run the `io_uring` version, it connects just fine:

```
$ ./target/debug/with_iouring 127.0.0.1:8000
written: 128
read: [102, 111, 111, 10]
```

It turns out you can setup `io_uring` with an allowlist
(counterintuitively referred to as a "restriction"), and this is
supported by the `io_uring` crate we used above if we dig enough to
find the [`register_restrictions`][] method. That works fine if the
seccomp filter is owned by the application as we've done in our
examples. The application can set up restrictions to drop its own
privileges prior to starting any I/O, just as it might become an
unprivileged user or use `unshare` to enter a restricted namespace.

But if you've got a separation of duties where a sysadmin sets up
seccomp filtering generically across applications, you won't be able
to take advantage of `io_uring` restrictions without cooperation from
the application developer. This most likely comes up with container
deployments. Docker and containerd have default seccomp filters that
allow `io_uring` (see where this was discussed in [moby/39415][] or
[containerd/4493][]).

Fortunately none of the available `io_uring` opcodes correspond to
syscalls filtered by those default seccomp filters, so there's no
privilege escalation available here by default. But it's certainly
something you might want to check up on if you're expecting seccomp
filtering to harden your applications.

[`io_uring`]: https://unixism.net/loti/
[TCP stream example]: https://github.com/tokio-rs/tokio-uring/blob/master/examples/tcp_stream.rs
[`seccomp` crate]: https://docs.rs/seccomp/latest/seccomp/
[`register_restrictions`]: https://docs.rs/io-uring/latest/io_uring/struct.Submitter.html#method.register_restrictions
[moby/39415]: https://github.com/moby/moby/pull/39415
[containerd/4493]: https://github.com/containerd/containerd/pull/4493
