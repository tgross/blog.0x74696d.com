---
categories:
- ops
date: 2018-04-07T00:00:00Z
title: Logging as Local Maxima
slug: logging-as-local-maxima
---

Over the last couple months I've been working on improvements to [our](https://www.density.io) ability to collect telemetry and determine the health of our embedded systems out in the field, and using the same set of systems to collect information from the server-side systems. These projects have had me thinking a lot about logging as a local maxima in the design space of observability.

What's a local maxima in a design space? Imagine all the possible ways of observing a system's behavior. Especially including the possible ways that we haven't discovered or invented yet. And now imagine that you could come up with some way of measuring these methods. It doesn't really matter if you're measuring them objectively or just for your organization in this case. If we then mapped this design space on a graph (or like a cool n-D skein!) we'd find that similar approaches cluster together in little peaks of awesome and valleys of crappiness. Some of those peaks will be higher than others. But if you find yourself on one of the low peaks and don't look too far away, everything else you see looks worse. If you're stuck on that local maxima then you might be missing out on finding some higher peak that's very different.

I suspect that logging is one of these local maximas. Now, a lot of energy (and VC money!) has been poured into _collecting_ telemetry from applications, whether its logs, metrics, APM, whatever. The companies involved in this space are strongly incentivized to tell you that they can observe arbitrary applications and it's not something you need to worry about past maybe logging in JSON rather than raw strings. Their value comes in making sense of that data, storing it cost-effectively, presenting it, and creating insights. All good stuff and often well worth the money! But not what I want to talk about -- I want to talk about the way we log.

> Seemingly obligatory aside: stop right there if you were about to correct me on whether logging is observability or monitoring, or whether observability is a noun or an adjective. Vendors: your customers don't give a shit about these definitional arguments! Trust me, I've been both vendor and customer and it's a total waste of time.

> Also, this is as good a time as any to remind you that I'm talking about my own experience and organization scale here. If you're working for Amazon or Google, my advice is probably worthless and y'all have figured all this out already. But if you're working in a 100 person org and having sticker shock over the monetary cost and engineering cost of telemetry, we might be on the same page here.

Some context: the immediate problem you run into with any Internet of Things deployment is that even a modest deployment means deploying many more devices than you'll be deploying servers. Even a small pilot program is deploying a number of devices rivaling the size of the server deployments of a mature mid-size startup.

Each one of those devices is a Linux box with a pile of applications on it. The telemetry traffic these things can potentially produce will totally swamp the traffic you're otherwise using to serve your business, unless you're doing something like streaming video from the device. In our case, because privacy is such a huge part of our value proposition, we do all the complex computational work on the device and only send back a trickle of event data ("1 person entered at timestamp T", "2 people exited at timestamp T+1"). The volume of which is strictly limited by the number of human beings that can physically fit through a given door (not that much!). Which means that when we started collecting remote telemetry for the first time it was an absolute _firehose_. Telemetry data was orders of magnitude the data with direct business value.

Moreover, this telemetry data is mostly _utter crap_. Third-party open source applications that say "I'm awake!" "Checking for work to do!" "Nothing to do!" "Sleeping for 30 seconds!" every 30 seconds 24/7/365. Stack traces being broken up into individual log lines. Java appplications that dump thousands of lines of those stack traces during normal non-error operations (seriously, Java people, what the hell is up with that?). That developer who added a `log.warning` line when a particular conditional was hit while hacking away during development and forgot to remove it. That developer who intentionally logs every "200 OK" with no other context.

## Practical Sampling

So you get to work and start filtering this stuff down. Does that service really need to log every time it wakes up? Can we turn down verbosity on this service? Can you pretty please wrap your damn stack traces? But you're still left with a huge volume of data, and most of it gets logged and never looked at again.

Then you start saying "well what if we sample the logs?" and some part of your team inevitably freaks out at this because how are they supposed to debug _anything_ if we can't be sure we've collected every. single. log. You quietly decide at this point not to remind them about backpressure or that GELF is sent over UDP. But they do have a point, but it's not just about sampling.

Let's look at a simple example application stack like the one in the diagram below. In a production deployment we've got some number of edge servers like Nginx (maybe themselves behind a managed load balancer), backed by some number of application servers. Because its 2018 and apparently we're all doing microservices, let's assume these applications need to talk to each other. Application A makes upstream requests to B and C, and C makes upstream requests to D. Any of these applications could just as well be databases or gRPC applications or whatever; it doesn't matter. Of course, there are multiple instances of each application for redundancy and scaling. It doesn't matter for this discussion whether these are separate processes, containers, Kubernetes pods, whether they're on different underlying VMs, etc.

# TODO: diagram

When our application makes a request, it hits a number of services and each of them does its own logging. There's no coordination of this effort among services. If we naively sample (say 5% of requests), then you get a disjoint view of the world. A given request might get logged by Application B but the log gets sampled out for Applications A, C, and D. The smaller your sample size the more likely it is that a given log entry is an "orphan" relative to all the other services.

What we need here is to coordinate our efforts, without requiring ongoing consensus among the services. This is surprisingly easy to do!

Every request should have an associated request identifier. If you control the client this can be added at the client but most of the time you'll add this at the edge server. Nginx has a nice option to use the `$request_id` variable. You add this to your logs and you pass it along to every upstream application (as a header if we're talking about HTTP).

For example, our Nginx configuration will add this as a field to its logs (you are logging in a structured JSON format, right?), and add it as a `X-Request-ID` header:

```
log_format main escape=json '{"timestamp": "$time_iso8601", "host": "$host", "req_id": "$request_id", "client_ip": "$http_x_forwarded_for", "elapsed": $request_time, "status": $status, "path": "$request", "bytes_sent": $body_bytes_sent}';

server {
    server_name example.com;
    listen 443;

    location / {
        proxy_pass http://example-upstream;
        proxy_redirect off;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header X-Request-ID $request_id;
    }
```

And then in our application we'll add this to our request context. In Django this might look like this inside a middleware function (we'll circle back to what to do with this in a moment):

```python
request.req_id = request.META.get('HTTP_X_REQUEST_ID', '')
```

This is great low-hanging fruit just in terms of understanding what the hell is going on between all your services, but that's not all -- you can consistently sample across all your services!

```python
import random
from settings import LOG_SAMPLE_RATE

# for Python 2 dinosaur code you need to cast this to a float
MAX_REQ_ID = int(('f' * 32), 16)

def take_sample(req_id):
    """
    use consistent sampling when request ID is available so that
    multiple services with the same sample rate are guaranteed to
    sample the same set of requests
    """
    try:
        return (int(req_id, 16) / MAX_REQ_ID) <= LOG_SAMPLE_RATE
    except (TypeError, ValueError):
        return random.random() <= LOG_SAMPLE_RATE
```

This snippet says that we divide our random 128-bit ID by the maximum ID and compare that ratio against the sample rate. So for example if our ID is `0ccccccccccccccccccccccccccccccc` it'll be sampled so long as our sample rate is 5% or more. And we know that that same request will be sampled across the entire stack.

The other important note here is that we don't have to sample all requests in the same way. Your health check that responds "200 OK" every 5 seconds is not an interesting thing to log. An error condition is. An unhandled exception definitely is (or better yet, crash and core dump so that the process's [body can be donated to science](https://youtu.be/AdMqCUhvRz8?t=1310)).

Again, in the Django universe where I'm working, you might have a block of code like the following in your middleware handler:

```python
if response.status_code not in LOG_STATUS_NEVER_SAMPLE \
    and request.path not in LOG_PATHS_NEVER_SAMPLE \
    and take_sample(request.req_id):
    logger.info('%s %s', response.status_code, request.path,
                extra={'status_code': response.status_code,
                       'req_id': request.req_id,
                       'sample_rate': LOG_SAMPLE_RATE,
    })
```

This assumes you have a log formatter configured to dump the [`extra` kwarg](https://docs.python.org/3/library/logging.html#logging.Logger.debug) along with the rest of the `LogRecord` fields to JSON. The configuration options here tell this logging middleware to ignore things like your health check but also to ignore exceptional status codes. So instead of logging a sample of HTTP500s, we'll let those bubble up to the next layers of middleware. Particularly for unhandled exceptions it's a good idea to send stack traces to a dedicated service like [Sentry](https://sentry.io) or core dump to something like [Joyent's `thoth`](https://github.com/joyent/manta-thoth) rather than just dumping them in your logs. But you certainly can extend your log formatter to log stack traces as a single log record as well.

The exact structure of where this lands in your code will vary. If you're writing golang this might instead be a `http.Handler` wrapper. If your organization hasn't drunk too much from the polyglot microservices kool-aid you can make this into a shared library and get some nice consistency across the org.


## Unit of Work

While this is all well and good for making logs suck less, we're firmly within our logging local maxima. But there's a small change we can make to the way we log that could make a major difference in the way we observe our systems, which is to push logging all the way out to the edge of your application and _log exactly once per unit of work_.

Here's an excerpt of a method from a real-world piece of good, solid, Django software that I'm not going to name because I don't want to sound like I'm picking on it at all.

```
class Page(AbstractPage, index.Indexed, ClusterableModel, metaclass=PageBase):

    def save_revision(self):
        revision = self.revisions.create(
                content_json=self.to_json(),
                user=user,
                submitted_for_moderation=submitted_for_moderation,
                approved_go_live_at=approved_go_live_at,
            )
        update_fields = []

        self.latest_revision_created_at = revision.created_at
        update_fields.append('latest_revision_created_at')

        self.draft_title = self.title
        update_fields.append('draft_title')

        if changed:
            self.has_unpublished_changes = True
            update_fields.append('has_unpublished_changes')

        if update_fields:
            self.save(update_fields=update_fields)

        # Log
        logger.info("Page edited: \"%s\" id=%d revision_id=%d", self.title, self.id, revision.id)

        if submitted_for_moderation:
            logger.info("Page submitted for moderation: \"%s\" id=%d revision_id=%d", self.title, self.id, revision.id)

        return revision
```

When an instance of this class has a revision saved, it creates a revision object of some kind, sets some fields on it, and saves it to the database. (I've haven't looked to see if the caller wraps this in a transaction but if not you should have `ATOMIC_REQUESTS=True` set.) But look at the end there. We emit one or two different log lines depending whether the page needs to be moderated. In addition, we have a top-level request logger from `django.request` that might be logging this request.

Let's assume we have a few instances of this application and multiple people "creating revisions" and calling this method. When we collect our logs from all the services we get a bunch of interleaved entries.


## TODO: diagram

We can definitely go back to our logging code from earlier and start adding additional context there. And then we can use our log viewing tools (let's say Elasticsearch) to filter down to a specific request. But if, but this only will include context that's global to the application and request: "What machine was this running on?" "Which process ID?" "Which request?" "Which session?"
