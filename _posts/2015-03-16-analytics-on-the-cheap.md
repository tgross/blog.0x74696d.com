---
layout: post
title: "Analytics on the Cheap"
category: ops, AWS
---

In November of 2013 I was at the AWS ReInvent conference, where they previewed their new service Kinesis. The long story short of this is that it's a hosted Kafka. And the long story short of Kafka is that it's a way to ingest a whole lot of data in the short period of time so that you can process it in some kind of near-offline process later. The seemingly canonical example is something like log data. Loggly uses Kafka for this, I hear? The premise is that you have a stream of data from many clients, you want those clients to be able to treat the messages as close to fire-and-forget as possible (within the boundaries of TCP, if you're using that as the transport), you don't want to drop messages, and you want to be able to get the messages into the system you're using for analysis as soon as possible.

But I would argue that in most cases outside of things like Loggly, you don't have actionable data when you're doing analysis real-time, so you can do the processing part as a batch job. Which changes the operational economics of the system quite a bit. There's no point in putting up the capital for near-realtime analytics if you don't need them, and you'd be surprised how close you can get and still keep things inexpensive.

The Firehose, Part Deux
----

In an earlier article I mentioned in passing that [we](http://www.dramafever.com/company/careers.html) at one point replaced a fairly complicated system using DynamoDB to ingest our analytics firehose. The solution we came to for that is what I want to talk about here. We're working under the following requirements:

- Large swing in load throughout the day (which implies efficiencies to be had in stateless auto-scaling instances).
- Response time to the client should be low-latency.
- Need to geolocate the client
- Need to authenticate the client (although we also handle anonymous clients)
- Need to be able to take the same data set and reuse it in other analysis environments in the future
- Might need to update the kinds of data we're collecting in the future
- As cheap as possible

The technique I'm describing has one important constraint: messages have to be either idempotent or have a built-in ordering (ex. time series data), because there's no way for the ingest servers to handle the ordering of messages otherwise. You won't be able to come up with a "true" total ordering here either, but we're okay with that on a statistical level.

The basic workflow is this:

- Incoming message passes through our CDN to pick up geolocation headers
- Message has its session authenticated (this happens at our routing layer in Nginx/OpenResty)
- Message is routed to an ingest server
- Ingest server transforms message and headers into a single character-delimited querystring value
- Ingest server makes a HTTP GET to a 0-byte file on S3 with that querystring
- The bucket on S3 has S3 logging turned on.
- We ingest the S3 logs directly into Redshift on a daily basis.

The first two layers aren't particularly interesting except that by the time we get to the analytics server we have a request that looks something like this:

**Example request: user watched a segment of video**

```
POST /tick/ HTTP/1.1
Host: https://api.example.com
Content-Type: application/x-www-form-urlencoded
Accept: application/json
User-Agent: VideoPlayerUserAgent
X-Akamai-Edgescape-Header: City=Splot,Country=Wales,Region=Europe
X-User-Id: 1234567
X-User-Type: Registered
X-Consumer: InternalCodeForConsumerType

event_guid=xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
event_type=watch
video_type=video
content_id=4
start_timecode=60
end_timecode=120
```

In practice we have a dozen extra fields on there and some of the names are different for weird historical reasons. But the point is that we've got this far with only ever hitting our session store once (if it's an authenticated session and if you're using a session store instead of signed/encrypted on-the-wire sessions) and making one hop thru Nginx.

Ok, so at this point we've got a request and we need to ingest this pretty quickly. The original design had a whole bunch of Flask processes running under gevent. You need multiple processes per box because the GIL starts to get in the way even if you're mostly I/O bound. Last summer we moved this to Go and I'm deploying less than 10% of the number of EC2 instances now.

The only thing our ingest server needs to do it to validate the message and then transform it into a querystring. For example, we make sure that the `content_id`, `start_timecode`, and `end_timecode` are all integers, that the `event_type` falls within a range of a few types, etc. Once we're done with that we transform the values of the fields into a single querystring parameter. Here's the catch: the order of the fields is immutable for all time. You can add fields by appending them and can remove fields by leaving the value out (but keeping the delimiters that mark it). But changing the order will break your old records.

So for our example we're going to have the fields in this order: event timestamp, event GUID, user id, user type, consumer, country, event type, video type, content ID, start, end. We make a signed GET to S3:

**Example request to S3**

```
GET /tick HTTP/1.1
Host: https://example.bucket.s3.amazonaws.com
X-Amz-Authentication: xxxxx

data=|2014-01-15T19:33:23|xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx|1234567|Registered|InternalCodeForConsumerType|Wales|watch|video|4|60|120|
```

(Notice that we start and stop with a pipe -- this will come up again later!)

In practice we use a short code for the various enums involved rather than writing out "InternalCodeForConsumerType" in the querystring. If the message fails to validate or, far less likely, the GET to S3 fails, we can either log this querystring for later reply or send it off to a queue for reprocessing later. If you don't have a lot of failed messages and having added latency between message arrival and analysis isn't a problem, just logging it out is probably cheaper. In our service we have few true errors but our validation is pretty strict (so we don't analyze a lot of garbage) and if a client has a buggy release then it'll send a flood of bad messages. So we sample validation errors and send those off to Sentry so the client developers can see them and fix their clients.

If you really care about latency of the initial request a lot, you can reduce S3 latency slightly by using multiple identical-to-your-application S3 keys. S3 suffers from hot-hashes -- although I've never noticed it at our scale -- so you can hash the requests among *n* keys in the same bucket and it won't matter to the final logging output.

Why sign the GET? Because we have the S3 bucket locked down so that only our ingest servers can make the GET. This prevents third-parties or incautious developers from messing around with our analytics data. Create an IAM user just for your ingest servers and use that AWS access key and secret key in your application to sign the request. Here's the IAM configuration you'll want for that user:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
      ],
      "Resource": [
        "arn:aws:s3:::example.bucket/tick"
      ]
    },
   {
```


Within an hour or so each GET shows up in the logs for the S3 bucket wherever we're sending the logs for our S3 `example.bucket` (for example, `example.bucket.logs`). At this point your possibilities for analysis are broad. If you have a small amount of data and just want to dick around with grep/awk, you can do that. If you have millions of messages a minute and need to pipe it to Redshift, you can do that. I'll get to that in a moment but let's have a short aside about operational costs of this system at this point.


How Cheap Is It?
----

So at this point you've got only 2 moving parts: the ingest web server and the S3 logging. The web server only has to be as beefy as the validation you do. In our case we're not hitting a database or doing any complicated operations; everything we're doing is just to make sure we don't write garbage data and to take note of problems (99% of the time this is from a new version of a client that's failing to meet spec).

How many instances you'll need is going to directly depend on the load you need to serve and your server's ability to handle concurrent connections. Python, even with gevent, is probably not ideal for this at large volumes but it's very quick to put together if you're just starting out. Let's assume our inbound request and our processed S3 message are both ~200B. Assuming we're using EC2 medium I/O instances like the new c4.large, we can put 10k messages/second in the pipe without even saturating the network connection. If you're running Flask, chances are your ingest server application will crap out first, so don't use that if you have 10k+ req/second. Use Go or Erlang or Java (yuck) or something. But our current Go application barely notices this kind of traffic. Once we did some very basic TCP and ulimits tweaking, we're only running as many instances as we do to support our internal standards for redundancy.

Our S3 bucket with the 0 byte file `tick` costs us only the cost of the S3 GETS. As of this writing that's $0.004 per 10k requests. This is all within-AWS, so there's no additional charge for data transferred (which would be very small anyways).

Our ~200B logging message takes us space in S3, so we'll be spending about $0.0006 in storage per 10k messages (up to the first 10 billion or so, when they get slightly cheaper). If we want, we can rotate the logs off to AWS Glacier after a few months and save a couple bucks that way.

At the end of the day, the design we have here now has a unit cost (per event captured) less than 1% of the original design of the application.


Slurping Up the Data
----

Doing any kind of analysis at this point probably means we need to ingest the data into a different format. I dunno about you, but sort, uniq, grep, awk get a little tiresome once we start working with hundreds of files with billions of rows each. At our scale we could probably just barely get away with a beefy MySQL instance (we've standardized on MySQL), but we decided to use AWS Redshift instead and have been pretty happy with it. One of the nice features it has is for this kind of ingest is that you can copy directly from s3.

The S3 log files are named for the hour in which they were created. Our quick-and-dirty way to deal with this for a daily roll-up is to create a new table for each day's raw rows (we do lots of post-processing in another step to figure out unique sessions, separate ads from video plays, etc.). We keep the raw tables for a while so we create one for each day, but if you don't want to do that you can just throw out the daily raw tables once you've post-processed them. As long as you keep the original logs in S3/Glacier (12 9's durability) you can always go back and re-process if there's a new kind of analysis you want to do. If we continue the example from above our raw table might look something like this:

```

CREATE TABLE raw_s3_rows (
    left_margin VARCHAR(600) ENCODE text32k,
    event_time TIMESTAMP ENCODE delta SORTKEY,
    event_guid CHAR(45) ENCODE raw DISTKEY,
    user_id INT4 ENCODE mostly8,
    user_type INT2 ENCODE mostly8,
    consumer CHAR(40) ENCODE bytedict,
    country CHAR(4) ENCODE bytedict,
    event_type CHAR(20) ENCODE bytedict,
    video_type CHAR(10) ENCODE bytedict,
    content_id INT4 ENCODE mostly8,
    start INT4 ENCODE mostly16,
    end INT4 ENCODE mostly16,
    right_margin VARCHAR(200) ENCODE text255
);
```

Note the two weird bits. The `left_margin` field lets us cut off everything we see left of the first delimiter in the log line, and the `right_margin` does the same at the end. That's why we started our querystring parameter with a pipe earlier. We don't have a lot of control over the logging format that S3 uses, so this should give us a guarantee that we know where the start and end of our data are. Obviously this will break big-time if you allow unauthenticated GETs to the S3 key you're using for logging because any asshole on the web can come along and stuff evil in there.

Now we can load in the raw S3 logs:

```

COPY raw_s3_rows
  FROM 's3://example.bucket.logs/log-$DATESTAMP'
  CREDENTIALS 'aws_access_key_id=<ACCESSKEY>;aws_secret_access_key=<SECRETKEY>'
  DELIMITER '|'
  TIMEFORMAT AS 'YYYY-MM-DD-HH-MI-SS'
  EMPTYASNULL
  BLANKSASNULL
  MAXERROR AS 1000;
```

Of course you'll want to automate this in some way to remove the `$DATESTAMP` bit and have that be the hourly log names. We bail out if we get a lot of errors in the loading process, but because of the kind of data we're dealing with we're okay if there are a few bad messages (in practice we catch this at the validation stage so if we're seeing errors it's because we did something dumb like added a field without also updating the `CREATE TABLE` script).

The important thing to notice here is that although we're doing a daily roll-up of the S3 logs, your ability to get the data faster is limited only by two things: how fast redshift can hoover-up the data from S3, and how good AWS's "best effort SLA" is on getting the logs into the S3 bucket (it's not bad... you could probably get away with getting logs within 2-3 hours without being worried about missing data).

Events as Audit Trail
----

Even not counting the analysis part, there's one more nice bit about this setup which is that it's modular and reusable across applications. We can imagine a poor-mans version of this for a static web site. Instead of signing the GET, a piece of Javascript on the page makes the GET (or a resource is loaded remotely like the classic 1x1 transparent tracking pixel). You can't validate the input or sign the request if you do this, which is probably dangerous, so don't go 'round telling your clients I said you should do this. But it's "infinitely" scalable -- if reddit decides to hit your blog your web server won't fall over serving analytics tracking.

But the really nice thing here is that these log events are just a bunch of files when you're done. The lines of the log can serve as an immutable event source -- so long as you only ever read from them. You can back them up to cold storage, use them in different data stores, treat them as your audit log, whatever you need.
