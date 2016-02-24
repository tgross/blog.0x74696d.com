---
layout: post
title: "Logging with Docker"
category: Docker
---

><aside>Hello from the future (November 2015)! Apparently this article has some good Google juice and so people still land here looking for guidance on logging in Docker more than 2 years later. Today Docker provides [log drivers](https://docs.docker.com/reference/logging/overview/) now that will let you send your logs off the host via syslog or other log shipping mechanisms. So please don't follow the advice in this article!</aside>

I spent a couple of days this week working on a new deployment design using [Docker](http://docker.io). Obviously Docker is a new project, so the documentation is a bit of a mess and not quite keeping up with progress on the code. You come to expect that on fast-moving open source projects, so we figured no biggie. But the one almost-deal-breaker for us was trying to figure out logging, so I thought I'd do a short write-up on that here.

# docker logs

Having a `docker logs` command available must be what threw me off. Docker captures all the `stdout`/`stderr` from the process you're running, and you can get the docker daemon to spit this out with `docker logs $CONTAINER_ID`. But if the process you're running is a long-running daemon, that's probably less than satisfactory. At first I thought I'd be clever and thought I could periodically run `docker logs >> /var/log/myapp.log`. Let's try that with a Django app on gunicorn and see what happens.

~~~ bash
$ ID=docker run myimage python manage.py run_gunicorn -b 0.0.0.0:8000
$ docker logs $ID
2013-08-03 18:45:05 [1710] [INFO] Starting gunicorn 0.14.2
2013-08-03 18:45:05 [1710] [INFO] Listening at: http://0.0.0.0:8000 (1710)
2013-08-03 18:45:05 [1710] [INFO] Using worker: sync
2013-08-03 18:45:05 [1713] [INFO] Booting worker with pid: 1713
$ # ok, let's do that again
$ docker logs $ID
2013-08-03 18:45:05 [1710] [INFO] Starting gunicorn 0.14.2
2013-08-03 18:45:05 [1710] [INFO] Listening at: http://0.0.0.0:8000 (1710)
2013-08-03 18:45:05 [1710] [INFO] Using worker: sync
2013-08-03 18:45:05 [1713] [INFO] Booting worker with pid: 1713
~~~

Uh oh. If I just append the output of `docker logs` I'll be writing the entire log out to the file each time. That's going to suck after a while. You don't want to use `docker logs` to write out logs for your process.

# mounted volumes

Instead you should bind a volume to the container and write your logs from your process to that mount point. This maps a location in the container's file system to a location on the host. You can then access the logs separately from the running process in your container and use tools like `logrotate` to handle them.

~~~ bash
$ ID=docker run -v /var/myapp/log:/var/log myimage python manage.py
  run_gunicorn -b 0.0.0.0:8000 --log-file=/var/log/gunicorn.log
$ docker logs $ID
$ # nada!
$ tail /var/myapp/log/gunicorn.log
2013-08-03 18:53:11 [1710] [INFO] Starting gunicorn 0.14.2
2013-08-03 18:53:11 [1710] [INFO] Listening at: http://0.0.0.0:8000 (1710)
2013-08-03 18:53:11 [1710] [INFO] Using worker: sync
2013-08-03 18:53:11 [1713] [INFO] Booting worker with pid: 1811
~~~

It's fair to note that attaching a volume from the host slightly weakens the LXC security advantages. The contained process can now write outside its container and this is a [potential attack vector](https://www.owasp.org/index.php/Log_injection) if the contained process is compromised.

Despite the documentation woes and a few minor headaches like figuring out logging, getting started with Docker was a lot of fun and I think it has a lot of potential. I'll be sharing more Docker stories here going forward.
