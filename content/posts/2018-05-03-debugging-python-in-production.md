---
categories:
- python
- performance
- Docker
date: 2018-05-03T01:00:00Z
title: Debugging Python Containers in Production
slug: debugging-python-containers-in-production
---

We all figure out our first Python bugs by sprinkling some `print` statements over our code. As we gain experience, our debugging toolbox becomes richer and we can figure out harder bugs in development. But production systems provide a different kind of challenge, and this challenge is amplified when we try to debug in a containerized environment. We need to be able to debug running code safely, without impacting performance or interfering with the user experience.

Some of the most powerful tools like debuggers or eBPF are the hardest to get working with Python containers, so in this post I'll cover methods to build Python containers for improved instrumentation and debugging. I gave a talk covering most of this content [Philadelphia Python Users Group (PhillyPUG)](https://www.meetup.com/phillypug/events/244306771/) last November. The original talk covered a bunch of material on logging but I'll revisit that in an upcoming post.

## Groundwork

Let's first assume that you've grabbed all the low-hanging fruit. You're collecting structured logs or events from your applications in a centralized location like [Elasticsearch](https://www.elastic.co/elk-stack) or [Honeycomb.io](https://honeycomb.io/). You're sending unhandled exceptions to something like [Sentry](https://sentry.io/welcome/). If you have a web application, you're tagging incoming web requests at the edge with something like [Nginx request IDs](https://www.nginx.com/blog/application-tracing-nginx-plus/). You can get really far with that! But it doesn't give you a detailed insight into how the application is behaving "under the hood", particularly in the cases where the application is failing in a way that isn't already known. [Bryan Cantrill](https://youtu.be/AdMqCUhvRz8?t=1215) calls these "implicit failure" modes.

With Python in particular, you can get insight into a lot of the application behavior with tools like [NewRelic](https://docs.newrelic.com/docs/agents/python-agent/getting-started/introduction-new-relic-python). But this is incredibly expensive to deploy across your whole production footprint, it can't really help with crashed applications, and it can't look into the Python interpreter or operating system underneath your code. I also find that the expense means that it doesn't get used in development or testing environments, and that makes for a gap in understanding.

The tools I'll discuss below do require some one-time up-front work, but the payoffs are enormous. First, to use native core dumps you need debugging symbols for Python. To use eBPF on Linux, you need to be on a modern Linux kernel (4.0+, or whatever frankenkernel RedHat is shipping these days). To use `usdt` probes for Python you need to be on Python 3.6+. But I've found most Linux distributions are not compiling-in the `usdt` probes, including the various Docker containers that ship Python. So we're going to want to build our own Python. Don't worry! This is much easier than it sounds!

## Building Your Python

The Docker Hub has a [Python image](https://store.docker.com/images/python) in its library. We need to slightly modify that build and make sure it's part of our continuous integration system. The source for the Dockerfiles is [on GitHub](https://github.com/docker-library/python/tree/master). We only care about Python 3.6 and above.

Python is written in C, and like many C applications under Unix it's built via Autotools. A `configure` step takes a Makefile template and some parameters, and generates a Makefile that we call `make` on to build the software. We want to alter the parameters that the Docker build is using to add debugging symbols (the `--with-pydebug` flag) and tracepoints (the `--with-dtrace` flag). So for example as of this writing, we'd be adding these flags to the template used for the `docker/python:3.6-slim` version [here](https://github.com/docker-library/python/blob/ba5711fb564133bf9c8b870b431682a4db427219/Dockerfile-slim.template#L61-L67). We also need to include the installation of `systemtap-sdt-dev`.


```diff
index 6799174..16dbbf0 100644
--- a/Dockerfile-debian.template
+++ b/Dockerfile-debian.template
@@ -19,6 +19,7 @@ ENV PYTHON_VERSION %%PLACEHOLDER%%
 RUN set -ex \
         && buildDeps=' \
                dpkg-dev \
+               systemtap-sdt-dev \
                tcl-dev \
                tk-dev \
         ' \
@@ -43,6 +44,8 @@ RUN set -ex \
                --with-system-expat \
                --with-system-ffi \
                --without-ensurepip \
+               --with-pydebug \
+               --with-dtrace \
       && make -j "$(nproc)" \
       && make install \
       && ldconfig \
```

The "best" way to accomplish this is going to depend a lot on how you build the rest of your software. But the overall steps you need are:

- Fork the https://github.com/docker-library/python and add the patch above to any of the templates you need.
- Have your CI system build the container images on a regular basis. You want to make sure you're pulling in any changes to both Python and the base Debian or Alpine image you're using.
- Have the output of the CI system be a push to your organization's private Docker registry (or even a public one if you don't mind sharing).

You can find my fork at https://github.com/tgross/docker-python. I'm using TravisCI to create a weekly build of Python 3.6 and 3.7 for Debian and pushing it to the Docker Hub under https://hub.docker.com/r/0x74696d/python/.

If you aren't using containers, don't have immutable infrastructure, and deploy your software via `git pull` in `ssh` in a for loop, then you'll probably want to do something like the following instead. This assumes you're on a Debian-based distro like Ubuntu and that you have a clone of the Python source code handy:

``` bash
# juuuuust a couple of dependencies...
sudo apt install \
    build-essential libssl-dev zlib1g-dev \
    libncurses5-dev libncursesw5-dev libreadline-dev \
    libsqlite3-dev libgdbm-dev libdb5.3-dev libbz2-dev \
    libexpat1-dev liblzma-dev tk-dev \
    systemtap-sdt-dev

./configure \
    --with-pydebug \
    --with-dtrace \
    --enable-loadable-sqlite-extensions \
    --enable-shared \
    --with-system-expat \
    --with-system-ffi \
    --without-ensurepip

make
make test
sudo make install
```

## Debugging From Sidecars

Container images don't typically include debugging tools. They add a lot to the image size, but they also require root-like privileges (ex. `ptrace`, `CAP_SYSADMIN`) and the whole point of a container is that you can run it with reduced privileges. So typically you'll debug a container either from the host (if you have access to the host) or from a "swiss army knife" sidecar container like the one you can find at https://github.com/tgross/swiss-army-knife

``` Dockerfile
# swiss-army-knife container for debugging as side-car
FROM ubuntu:16.04

# add whatever tools you want here
RUN apt-get update \
    && apt-get install -y \
       gdb \
       strace \
       tcpdump \
       linux-tools \
       software-properties-common \
       apt-transport-https \
       ca-certificates \
       curl \
       jq \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository "deb [trusted=yes] https://repo.iovisor.org/apt/xenial xenial-nightly main" \
    && apt-get update \
    && apt-get install -y --allow-unauthenticated bcc-tools \
    && rm -rf /var/lib/apt/lists/*
```

In either case you need to be aware of process namespaces. When you run a process in a container, it can't see all the other processes running on the host. In our Python container, the first process in the process tree (PID1) is typically going to be Python. Whereas PID1 on the container host is `systemd` or some other init system. You need to know which view of the process tree you have when you pass the process ID to your debugging tools.

If we look at the process tree from the host we get one list of processes:

```
$ ps afx

 PID COMMAND
...
1155 /usr/bin/dockerd -H fd://
1350 \_ docker-containerd -l unix:///var/run/docker/libcontainerd/docker-containe
22176 | \_ docker-containerd-shim a1e9578bfc58fb130a8b02fb413fc1579a4885a3fa0751
22193 | | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
31786 | | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
  479 | | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
22879 | \_ docker-containerd-shim 6b6e053851cabc2e257e79ef130c140132d30d935e194b
22896 | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name anotherapp
 3965 | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name anotherapp
 4153 | \_ /usr/local/bin/python /usr/local/bin/gunicorn --name anotherapp
...
```

Whereas if we look at the process tree from inside the container we'll get a different list:

```
$ docker exec -it 6b6e053851ca ps -ef

 PID COMMAND
   1 {gunicorn} /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
3446 {gunicorn} /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
3453 {gunicorn} /usr/local/bin/python /usr/local/bin/gunicorn --name myapp
```

If we want to run the eBPF tool `pythoncalls` (see below) from the host, we need to use the PID from the point-of-view of the host: `sudo /usr/share/bcc/tools/pythoncalls 479`. If we want to run this from a sidecar container, we need to use the container's view of the PID tree, share the process and network namespace, and give our sidecar elevated privileges for debugging:

``` sh
docker run -it \
    --pid=container:6b6e053851ca \
    --net=container:6b6e053851ca \
    --cap-add sys_admin \
    --cap-add sys_ptrace \
    swiss-army-knife \
    /usr/share/bcc/tools/pythoncalls -p 1
```


## Fatal Failure

A fatal failure is one in which the process dies. This can be explicit &mdash; the program has an instruction that tells it to exit because it can't safely continue. Or it can be implicit &mdash; the program can't continue and crashes unexpectedly (for example, with a segfault or Python traceback). While fatal failure is unfortunate from the perspective of the user, it's often much easier to debug.

The reason is that whether implicit or explicit, fatal failure allows for post-mortem debugging. We can start with the fatal state (a core dump), and move it off the production environment into our development environment where it can be examined with a lot less pressure. We use tools (our debugger) to reason backwards from the fatal state to a root technical cause. (Yes, yes, I realize there's no such thing as "root cause" in a complex socio-technical system. We're talking about the root *technical* cause here.) The nice thing about this is that so long as the state was preserved we can typically discover the cause after a single failure.

Python has its `pdb` debugger, but doesn't have a facility for dumping Python interpreter state to use it offline. If you attach `pdb` to a running process, it halts the process (which your users will not like), but you can't use it to debug post-mortem either. A Python traceback is only serializable in the trivial sense (dump to structured text), which is what services like Sentry use. Fortunately we can get core dumps from Python that are usable in the GNU debugger `gdb`.

When the Python interpreter receives a `SIGABRT` signal, it dumps the interpreter's memory to a core file on disk. On Linux we can use `gdb` to read this core dump just as we would any other program. But what's cool about Python being interpreted is that your Python source code is all in the interpreter's memory, so `gdb` has some extensions that let us debug into the Python application code just as we would the interpreter.

Under normal circumstances, Python won't dump core. We can send the `kill` signal to it manually, but there's another option &mdash; we can force Python to dump core on uncaught exception. I would only recommend this approach if you have good test coverage and are generally confident in your team's ability to write code that rarely crashes, as core dumps can get really large and eat up all your disk space unless you have something like [Joyent's Thoth](https://github.com/joyent/manta-thoth) to move them off-disk to shared object storage. Here's how you'd add this to something like a Django middleware:

``` python
import os
import logging

logger = logging.getLogger(__name__)

class AbortOnUncaughtExceptionMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.error(exception)
        os.abort()
```

This causes the application to crash and core dump if an exception wasn't handled. You probably want this to be the last middleware that gets called (so first in the list for Django) so that you can catch things like HTTP 404s more gracefully. Of course you'll also need your supervisor (`systemd` or similar) to restart the process after it crashes.

On `systemd`-based systems, core dumps are handled by `coredumpctl`. We can use `coredumpctl` to output to a file which we'll then move to our development environment. Here we're taking the first python3.6 dump listed by `coredumpctl` and outputting it to the file `api.coredump`.

```
$ coredumpctl list
TIME PID UID GID SIG PRESENT EXE
Wed 2017-11-29 18:06:08 UTC 7858 0 0 6 * /usr/local/bin/python3.6
Wed 2017-11-29 18:06:18 UTC 7872 0 0 6 * /usr/local/bin/python3.6
Wed 2017-11-29 18:06:25 UTC 7881 0 0 6 * /usr/local/bin/python3.6
Wed 2017-11-29 18:07:21 UTC 7890 0 0 6 * /usr/local/bin/python3.6
Wed 2017-11-29 18:07:29 UTC 7914 0 0 6 * /usr/local/bin/python3.6

$ sudo coredumpctl -o api.coredump dump /usr/local/bin/python3.6
```

Once we have the core dump locally, we can load it into `gdb` and import the Python-specific tools to list source code, move up and down the stack, read Python backtraces, and print the values of variables. For a detailed treatment of using the `gdb` debugging tools see https://devguide.python.org/gdb/.

```
$ PYTHONPATH=/src/cpython/Tools/gdb gdb python3 api.coredump
...
(gdb) python import libpython
(gdb) py-list
  11        def __call__(self, request):
  12            return self.get_response(request)
  13
  14        def process_exception(self, request, exception):
  15            logger.error(exception)
 >16            os.abort()

(gdb) py-up
(gdb) py-locals
self = <AbortOnUncaughtExceptionMiddleware(get_response=<function at remote 0x7fc98848d4a8>) at remote 0x7fc9884b64d0>
request = <WSGIRequest(environ={'wsgi.errors': <WSGIErrorsWrapper(streams=[<_io.TextIOWrapper at remote 0x7fc990140898>]) at remote 0x7fc9883c25a0>, 'wsgi.version': (1, 0), 'wsgi.multithread': False, 'wsgi.multiprocess': False, 'wsgi.run_once': False, 'wsgi.file_wrapper': <type at remote 0x140a698>, 'SERVER_SOFTWARE': 'gunicorn/19.7.1', 'wsgi.input': <Body(reader=<LengthReader(unreader=<SocketUnreader(buf=<_io.BytesIO at remote 0x7fc9883c01f0>, sock=<socket at remote 0x7fc9883af3b8>, mxchunk=8192) at remote 0x7fc98ace5c88>, length=0) at remote 0x7fc9883c26d8>, buf=<_io.BytesIO at remote 0x7fc9883c0410>) at remote 0x7fc9883c2740>, 'gunicorn.socket': <...>, 'REQUEST_METHOD': 'GET', 'QUERY_STRING': '', 'RAW_URI': '/histo/10/-1', 'SERVER_PROTOCOL': 'HTTP/1.1', 'HTTP_HOST': 'localhost:8000', 'HTTP_USER_AGENT': 'curl/7.47.0', 'HTTP_ACCEPT': '*/*', 'wsgi.url_scheme': 'http', 'REMOTE_ADDR': '127.0.0.1', 'REMOTE_PORT': '55272', 'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': '8000', 'PATH_INFO': '/histo/10/-1', 'SCRIPT_NAME': ''}, p...(truncated)
exception = Exception('uh oh',))
```


## Non-Fatal Failure

In contrast to fatal failures, non-fatal failures are sometimes the hardest problems to solve. These are the "unknown unknowns" of software engineering. Maybe your application is writing corrupted data. Maybe your application mysteriously runs slowly or freezes every few minutes. Maybe your application unexpectedly drops network connections. None of this is magic!

These kinds of problems are often impossible to replicate in a development environment, especially when we're talking about the kinds of distributed systems that tend to pop up when we're working with containers. We need _in-vivo_ analysis. And that means using tools like DTrace (for Unix) or eBPF (the closest Linux equivalent). Because for better or worse most folks are deploying production on Linux, we'll talk about eBPF here. The general concepts are similar to DTrace but DTrace is much more mature and frankly nicer to work with.

The Linux kernel includes a sandboxed bytecode interpreter that was originally created for IP tables filtering (Berkeley Packet Filter or BPF). In the 3.15+ kernel this bytecode interpreter has been extended allow user-defined programs to instrument a live system with minimal performance impact. To create these user-defined programs, we can use the [BCC](https://github.com/iovisor/bcc) toolkit. Programs are written in Python (or Lua) and compiled using LLVM to the eBPF bytecode. The eBPF programs read kernel instrumentation (kprobes) or user statically-defined trace points (`usdt`). What's really cool is that the outputs of the program are stored in buffers shared between kernel space and user space, so there's no inefficient copying of the data.

![eBPF](/images/20180503/eBPF-diagram.png)

See also the [bpf(2) man page](http://man7.org/linux/man-pages/man2/bpf.2.html)

The BCC toolkit comes with a ton of useful example tools. Want to sniff SSL traffic before the OpenSSL library encrypts it? Try [`sslsniff.py`](https://github.com/iovisor/bcc/blob/master/tools/sslsniff.py). Want to figure out your DNS lookup latency? Try [`gethostlatency.py`](https://github.com/iovisor/bcc/blob/master/tools/gethostlatency.py). Want to monitor I/O of your disks? Try [`biotop.py`](https://github.com/iovisor/bcc/blob/master/tools/biotop.py). Brendan Gregg has a great diagram of where all the various tools appears here: http://www.brendangregg.com/Perf/linux_observability_tools.png

In addition to being written in Python, BCC ships with a tools that are useful for instrumenting Python applications. If you have ever tried to profile a Python application you may have tried [`cProfile`](https://docs.python.org/3.6/library/profile.html). But it has a performance impact on the application and you can't add it to a running production application after the fact. Instead you can use the [`ucalls.py`](https://github.com/iovisor/bcc/blob/master/tools/lib/ucalls.py) library (or its handy [`pythoncalls`](https://github.com/iovisor/bcc/blob/master/tools/pythoncalls.sh) wrapper). This hooks the usdt endpoints that we made sure our Python interpreter had when we built it earlier with the `--with-dtrace` flag. Here we use it on a Django application that makes calculations via `numpy`:

```
sudo /usr/share/bcc/tools/pythoncalls 30695
Tracing calls in process 30695 (language: python)... Ctrl-C to quit.
^C
METHOD                                                                  # CALLS
<frozen importlib._bootstrap_external>.__init__                               1
/srv/venv/api/lib/python3.6/site-packages/django/vi._EnsureCsrfToken          1
/srv/venv/api/lib/python3.6/site-packages/django/co.get_path_info             1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib.poly1d                    1
/srv/venv/api/lib/python3.6/collections/__init__.py.update                    1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib.DummyArray                1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib.vectorize                 1
/srv/venv/api/lib/python3.6/site-packages/django/te.__init__                  1
/usr/local/lib/python3.6/logging/__init__.py._checkLevel                      1
/srv/venv/api/lib/python3.6/site-packages/numpy/cor.<listcomp>                1
/srv/venv/api/lib/python3.6/site-packages/numpy/lin._determine_error_states   1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib.ConverterLockError        1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib._set_function_name        1
/srv/venv/api/lib/python3.6/site-packages/numpy/ma/.mr_class                  1
/srv/venv/api/lib/python3.6/site-packages/numpy/cor._typedict                 1
/srv/venv/api/lib/python3.6/site-packages/numpy/ma/._convert2ma               1
/srv/venv/api/lib/python3.6/site-packages/numpy/lib.deprecate                 1
/usr/local/lib/python3.6/unittest/case.py._Outcome                            1
/srv/venv/api/lib/python3.6/enum.py.__and__                                   1
/srv/venv/api/lib/python3.6/site-packages/django/ut.find_module               1
...
```

In addition to `pythoncalls`, there's `pythonflow` to trace execution flow, `pythongc` to summarize garbage collection events, and `pythonstat` to collect counts of exceptions, imports, or method calls. (These are actually all wrappers around a library of `usdt`-reading tools that work for Python, Ruby, Java, or PHP.)

Happy debugging!
