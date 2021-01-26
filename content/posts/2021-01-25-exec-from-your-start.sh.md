---
categories:
- development
date: 2021-01-25T12:00:00Z
title: Exec from Your start.sh
slug: exec-from-your-start-script
---

At some point I noticed that some large portion of containers I've
seen have some kind of `start.sh` script file doing some setup and
then calling the actual application. Unfortunately a ton of these
break features of the application server. Like the previous post on
dropping signals, the way this typically manifests is the application
server can't reload configuration or gracefully shut down.

Your standard user-friendly web frameworks run your code inside an
application server. This is what opens up a port, accepts connections,
and turns the data that comes into over those connections into some
kind of "request object". Usually this will be a library separate from
your framework with some of its guts written in C, and the framework
will support a few options for servers. For Django this might be uwsgi
or gunicorn, for Rails it might be puma or unicorn, and for Spring it
might be Tomcat or Jetty.

Most of these application servers have a bunch of nice features that
rely on signals, to reload the configuration, do graceful shutdown,
add extra worker processes, or whatever. And then some unlucky
developer gets handed a Dockerfile and gets told they have to use
that. But they have to load some config or do some setup at start
up. They look up how to do it and systemd has some `ExecStartPre`
thing but this container stuff doesn't. And no one has ever bothered
to teach them what this is supposed to look like because developers
are only supposed to care about business logic anyways. So we end up
with a process tree in the container like this:

```
$ ps f -o pid,comm
  PID COMMAND
    1 /bin/sh start.sh
    8  \_ /usr/local/bin/gunicorn
   21     \_ gunicorn worker
   22     \_ gunicorn worker
```

Now the orchestrator wants to tell the application to reload its
config and it sends a `SIGHUP` to the container. By which we mean
PID1 in the container, which is our `start.sh` script. It doesn't know
anything about signals, so it dies and takes the application with it.

If you're using Docker you might have a
[`tini`](https://github.com/krallin/tini) init process in there as
PID1 that'll pass signals to the `start.sh` script, but the result is
the same because the signals never reach the application server.

```
$ ps f -o pid,comm
  PID COMMAND
    1 init
    7 \_ /bin/sh start.sh
   21     \_ /usr/local/bin/gunicorn
   22        \_ gunicorn worker
   23        \_ gunicorn worker
```

What we wanted to do is to call `exec` in our `start.sh` script. Then
the process tree looks like this:

```
$ ps f -o pid,comm
  PID COMMAND
    1 /usr/local/bin/gunicorn
    7 \_ gunicorn worker
    8 \_ gunicorn worker
```

Doing this also means we can just set export environment variables in
the shell script and they'll be set in our new application server
process. A minimal working example looks like the following.

Here's our mock application:

```go
func main() {
    c := make(chan os.Signal, 1)
    signal.Notify(c, syscall.SIGINT)

    for _, env := range os.Environ() {
        fmt.Println(env)
    }
    <-c
    fmt.Println("\ngraceful shutdown!")
}
```

Our minimal startup script:

```
#!/bin/sh
export SUPER_SECRET_FROM_VAULT=xyzzy
export PLATFORM=$(uname)
exec printenvvars
```

And our Dockerfile:

```
FROM busybox:1
COPY printenvvars /bin/printenvvars
COPY start.sh /bin/start.sh
ENTRYPOINT ["/bin/start.sh"]
```

We build that with `docker build -t test .` and now let's run it:

```
$ docker run test
HOSTNAME=741960aa5144
HOME=/root
SUPER_SECRET_FROM_VAULT=xyzzy
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PLATFORM=Linux
PWD=/
^C
graceful shutdown!
```

Note this will hang until we hit Ctrl-C, which sends `SIGINT` to PID1
in the container. At that point the channel in our application
unblocks and we see the graceful shutdown message.
