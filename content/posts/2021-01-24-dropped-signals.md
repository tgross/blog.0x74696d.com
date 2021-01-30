---
categories:
- development
- golang
date: 2021-01-24T12:00:00Z
title: Dropped Signals
slug: dropped-signals
---

A lot of go applications try to do something clever with signals and
end up dropping signals on the floor. I've definitely written this
kind of bug myself. It's not a community practice to lean on an
application server rather than the stdlib, so that creates an
opportunity for folks to incorrectly implement it from scratch.

Note that we're not talking about
[`signal-safety(7)`](https://man7.org/linux/man-pages/man7/signal-safety.7.html). For
purposes of this discussion we're going to merrily assume the authors
of [`os/signal.Notify`](https://golang.org/pkg/os/signal/#Notify) have
avoided any signal-unsafe code. Although it'd be neat to dig into how
that worked out with the go scheduler at some point.

The docs for `os/signal.Notify` say:

> Package signal will not block sending to c: the caller must ensure
> that c has sufficient buffer space to keep up with the expected
> signal rate. For a channel used for notification of just one signal
> value, a buffer of size 1 is sufficient.

We have to read this a bit carefully; it says a buffer of size 1 is
sufficient for one signal _value_, which is not the same as one signal
type.

Suppose we have a server that can reload its configuration on `SIGHUP`
and does a graceful shutdown on `SIGINT` (or `SIGTERM`). If we're in
the middle of doing a configuration load and get a shutdown notice,
we'll queue-up the shutdown signal and process it afterwards. The
signal mask is still in place, so any other signal sent during that
window will get dropped.

```go
func main() {
    c := make(chan os.Signal, 1)
    signal.Notify(c, syscall.SIGINT, syscall.SIGHUP)

    for {
        s := <-c
        switch s {
        case syscall.SIGHUP:
            fmt.Println("Got SIGHUP, reloading config...", s)
            time.Sleep(1 * time.Second)
        case syscall.SIGINT:
            fmt.Println("Got SIGINT, gracefully shutting down...", s)
            time.Sleep(1 * time.Second)
        }
    }
}
```

If we run this program in one terminal and then send it 3 signals in a
row, we can see we drop one of them.

```sh
# first terminal
$ go run .
Got SIGHUP, reloading config... hangup
Got SIGHUP, reloading config... hangup

# second terminal
$ pkill -SIGHUP signals; pkill -SIGHUP signals; pkill -SIGINT signals
```

This would be a catastrophic bug in an init system or process
supervisor (and/or something like
[ContainerPilot](https://github.com/joyent/containerpilot), where it
actually was a bug in early versions). We need to catch `SIGWAIT` to
reap zombie processes. It'd also cause dropped signals for an
interactive terminal application, where we'd probably masking
`SIGWINCH` to detect terminal window size changes.

But for most web applications this isn't a huge deal. Typically where
this bites us is if we have an orchestration layer that sends `SIGINT`
or `SIGTERM` for graceful shutdown and then kills the process
unceremoniously after a timeout. But there's some kind of automated
process that's picking up changes from the environment and firing
`SIGHUP` to do a config reload. If we drop the graceful shutdown
signal because we're stuck in a config reload, then the orchestrator
sends an interrupt that the application ignores. After 10 seconds or
whatever your timeout is, the orchestration says "whelp, I give up"
and sends a `SIGKILL`. And then our application drops in-flight
requests and users are unhappy.
