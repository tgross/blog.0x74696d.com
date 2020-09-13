---
categories:
- Docker
date: 2015-07-06T00:00:00Z
title: Running a host-local Docker Registry
slug: host-local-docker-registry
---

One of the options for running a private Docker registry is to run your own with the Docker Registry daemon. When [we](https://www.dramafever.com) started using Docker this was our approach from the beginning. At the time the Docker Registry was a Python app running on `gunicorn`; the new version is written in Go. A nice feature is that one can use S3 as the backing store, which *almost* makes the registry a proxy to S3.

But we ran into a pretty serious problem with it early on in terms of scalability. If we had to scale up a bunch of queue workers all at once to take on additional load in the application, we could overload the EC2 instance the Docker Registry was running on pretty trivially &mdash; if nothing else then with network I/O limitations. We could have probably gotten away with scaling up the box a lot, but this would leave a scary SPOF in our system and make moot the reliability of S3.

Instead we have the registry daemon as a host-local service backed by S3. So that means we have a container running the registry on the host, and we have a CNAME like `docker-local.example.com` that points to it. When a service starts it just does `docker pull docker-local.example.com:5000/my-service:tag`, and the Docker Registry backend retrieves the image layers from S3. The IAM role given to the production nodes has read-only access to the S3 bucket and can never push to it.

We use Jenkins to build and ship the containers. My colleagues [Bridget and Peter](https://www.youtube.com/watch?v=8fcDZB-QMRA) talked about this in depth at this year's ChefConf. And one of our team's alumni [Jeff](https://www.youtube.com/watch?v=yU0QhhS-XzI) talked about GrubHub's implementation of a very similar setup at Dockercon a couple weeks ago. Our Jenkins server has the same host-local Docker Registry setup, but has IAM permissions to write to the S3 bucket. As the sole node allowed to write to S3, we avoid any possibility of data races on the backing store. (If you need multiple writers you'll want to shard which repositories they write to by namespace.)

With this setup, network I/O throughput on start is limited only by the host that requires a new image and whatever S3 can give us. This lets us scale up nodes as fast as AWS can give them to us without worrying about the registry as a point of failure.
