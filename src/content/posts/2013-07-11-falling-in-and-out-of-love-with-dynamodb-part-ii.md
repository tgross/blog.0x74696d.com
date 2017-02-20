---
categories:
- AWS
- DynamoDB
date: 2013-07-11T00:00:00Z
title: Falling In And Out Of Love with DynamoDB, Part II
slug: falling-in-and-out-of-love-with-dynamodb-part-ii
---

Amazon's DynamoDB provides high concurrent throughput, availability across multiple AWS data centers, and the convenience of pay-as-you go pricing. All this is great, but key design for DynamoDB results in some unexpected challenges. [We](http://www.dramafever.com) have built a number of production systems at this point using DynamoDB and as such have a bit of a love/hate relationship with the product.

><aside>In my <a href="{% post_url 2013-06-18-falling-in-and-out-of-love-with-dynamodb %}">last post</a> I put up my slides from a talk by this same title. But sharing slides for a talk online without video isn't all that useful, so this is an attempt to distill the essence of a few of my points in the talk to something more comprehensible.</aside>


Schema-less-ish
----

DynamoDB is schema-less, but the design of your keys has a big impact on application design, throughput performance, and cost. Table rows are referenced by primary key: either a hash key or a hash key and range key. Range keys are sorted but -- this is the big catch -- they are sorted only within a given hash key's bucket. Hash key queries are exact, whereas range key queries can be conditional; you can ask for the range key portion to be "starts with" or "greater than".  If you have a hash-range key want to use the API and not spin up map-reduce (effectively, for anything soft real-time), you need to query the hash key and range key together.

![range key sorting](http://0x74696d.com/slides/images/20130618/dynamo-hashrange.png)

For the example schema above, I can do a query for all items where `hash == 1`, or all items where `hash == 1` and `range > b`.  But I can't make an API query for all items where `range > b`.  For that I need to do a very expensive table scan or send it off to map-reduce.

Our fan/follow system uses DynamoDB's weird key structure to its advantage. *Full disclosure: someone on our team smarter than me came up with this.* This feature lets us create relationships between arbitrary entities on our site. So a user can become a "fan" of an actor or a series or "follow" another user (under the hood this is the same data structure). In other words, we're looking to create a graph database.

![graph database](http://0x74696d.com/slides/images/20130618/graph.png)

For this, we use the following key schema:


    hash key                 |   range key
    -------------------------------------------------------------
    content_type.entity_id   |   FAN_OF.content_type.entity_id
    content_type.entity_id   |   FANNED_BY.content_type.entity_id


For each relationship we make two writes; one in each direction of the graph. Note that the range keys are all strings, which means having a delimiter and type coercion of integer IDs. Using the API to query this is stupid-easy. Say I want to know which actors a given user is a fan of. Using the `boto` library it's something like this:

``` python
results = table.query(hash_key=user_id,
                      range_key=BEGINS_WITH('FAN_OF.Actor.'))
```

Or I can run it backwards, and find out which users have fanned a given actor:

``` python
results = table.query(hash_key=actor_id,
                      range_key=BEGINS_WITH('FANNED_BY.User.')
```

For this sort of thing DynamoDB is awesome. The use case matches the structural quirks perfectly, and the pay-as-you-go pricing is great for what was at the time an unproven feature.

The Firehose
---

We started running into real trouble when we wanted to use DynamoDB for time series data. I'm not saying DynamoDB is unsuited for time series data, but the gotchas start to multiply rapidly. Our use case here was our analytics "firehose"; a ping that each of our video player clients sends back every minute containing a bunch of data we need for metrics, revenue-sharing data, etc. In other words, business critical and high volume. Originally all this data was going into a giant append-only MySQL table, but with something like 70% of all our requests resulting in writes to this table the performance was getting to be terrible as we scaled-up.  We could have sharded the MySQL database, of course. But an eventually-consistent lock-free database that supported widely-parallel writes seemed like an ideal use case for DynamoDB.

A naive approach to the key schema went like this:

    hash key        | range key   |  attributes
    ---------------------------------------------------
    series.episode  | timestamp   |  session_id, etc.

So if we needed data for a given series and episode, we can query and then slice on the range. But if you want a whole month's worth of data for, say, cutting your monthly revenue-sharing checks to content licensors, you're going to run an EMR job. And there are two additional problems.  The first is that the time it takes to run that EMR job will increase over time as the number of properties grow. I'll get to the second problem in a moment.

When we took a second crack at the design for this, we ended up having this conversation a lot:

<blockquote>
"Hey, you know in MongoDB you can..."<br/>"Nope, hierarchical keys, remember?"
</blockquote>

or this one:

<blockquote>
"Well in Redis you can..."<br/>"Nope, hierarchical keys, remember?"
</blockquote>

So this was the second attempt / dirty hack:

    hash key  | range key   |  attributes
    ------------------------------------------------------------
    day       | timestamp   |  session_id, series, episode, etc.


You still end up having to do a scan with EMR, but only over the data from a given day. Then you can aggregate data for series and episodes based on the attributes. You'll also need to roll-up tables as you go to reduce the amount of processing.  This is a bad hack, because you end up with write throughput that looks like this:

![cloudwatch with bad throughput](http://0x74696d.com/slides/images/20130618/thruput-badhashkey.png)

That's right, the throughput is a tenth of what we provisioned. This is where the abstraction of the managed service starts to leak. When you provision throughput, Amazon is spinning up `n` instances of whatever the underlying processes are. Your provisioned throughput is distributed among these instances.

![bad key distribution](http://0x74696d.com/slides/images/20130618/dynamotalk-keydistribution-bad.png)

Rows are written to the instances based on the hash key, not the combined hash+range key. Duh, it's a hash, right?  Which means in the schema above, we have a hot hash key, and with a hot key, throughput will be `(provisioned throughput / however many instances Amazon has provisioned)`. The number of instances is undocumented and abstracted from you but I've been able to estimate there are roughly 10 instances running when write throughput ranges between 200-500.

![good key distribution](http://0x74696d.com/slides/images/20130618/dynamotalk-keydistribution-good.png)

Avoiding hot hash keys is key to DynamoDB performance.  Because the throughput is divided by the number of instances, you end up with not just reduce throughput when you're writing to a single hash but *diminishing returns* on the throughput you provision. This was also the second problem with using series/episode as a hash key.  There's plenty of key space given the size of our library, but too many hot writes because the latest episodes tend to be the most popular.

Another thing to keep in mind here is that writes are at least 5x as expensive as reads. A unit of read capacity gets you 1 consistent read up to 4KB (or 2 eventually consistent reads), whereas the write unit is for 1KB writes. This doesn't include secondary indexes, which add another increment in cost for each index. So writes can be significantly more expensive.

Key design impacts throughput for both reads and writes, and the size of rows and number of secondary indexes impacts the ratio of writes vs reads. And because provisioning for DynamoDB is pay-as-you-go, this means *there is a direct relationship between key schema design and operational cost.*

Time Series Data
----

It is possible to do time-series data in the hash key, but only barely. You can add a random token to the end of timestamp that provides enough active key space to avoid a hot hash key. Then when you process the job in map-reduce, you remove that token.

    hash key                  | range key    |  attributes
    -----------------------------------------------------------------
    timestamp + random token  | session_id   |  series, episode, etc.

A two-ASCII-character token is enough to give you plenty of key space. Note that this makes it impossible to make API-based queries, because you'll need to make thousands of queries per timestamp you want to grab. You can *only* query this schema with map-reduce.

><aside>I had a chance to talk to some of the DynamoDB team recently about this approach and it's pretty clear this is a wrong-headed plan of attack they would probably not recommend. But at the time secondary indexes weren't available and in this use case we didn't need to query via the API. So we ran with this for a while despite some serious warts.</aside>

This design makes the writes simple and reduces the cost of doing ingest, but adds operational complications. In order to reduce the time it takes to do post-processing, you're going to want to roll-off data that you've processed by rotating tables. For us this meant doing a monthly rotation of tables, but the time it took to do a month's worth of data was impractically long and we wanted to eventually be able to shrink the processing window down so that our management team could use this for actionable BI (i.e. no more than 24 hours old).

You are *much* better off using a secondary index on an attribute which is a timestamp. Your row-writes will double in cost, but it'll be worth the greatly reduced complication and cost of your post-processing in EMR.

><aside>We ultimately replaced this entire system with a fun hack using a handful of evented Flask servers making 0-byte GETs (with appended query-strings) against S3 and ingesting S3 logs into Redshift. This reduced costs to a fraction of what they were but I'm going to leave that discussion for another time and an upcoming jointly-written post with one of our senior developers.</aside>


Throttling
----

One of the other problems we ran into with DynamoDB is dealing with throttling. Estimating the required provisioned throughput was pretty easy, but the load is also spiky. Our content team might post a new episode of a popular series and then announce it via social channels in the early evening, for example, and this will result in a sharp increase in new streams as those notifications arrive.

At the time we started this analytic ingest project, DynamoDB would throttle you fairly quickly if you went over provisioning. What's worse, the monitoring in Cloudwatch has poor resolution (minimum of 5 minutes average intervals), which means you could conceivably be throttled without it showing up in your alarms system until it's too late. If you are using a blocking backend (ex. Django), you're going to block the web thread/process if you are throttled. Amazon has provided a bit more leeway in throttling than they used to, but this only reduces the problem. Cloudwatch metrics for DynamoDB currently lag by 10-15 minutes, although at least the Cloudwatch monitor uses the same units as your provisioning, which wasn't the case when we started out.

If your application allows for eventual consistency as our analytics ingest project did, you can avoid throttling problems by making your writes asynchronous. Our pipeline took the incoming pings, pre-processed them, placed them into a queue (we use SQS for this, but RabbitMQ is another good option), and then pulled the messages off the queue with a worker that makes the writes. If we have load spikes or a failure in the workers, we can safely allow messages to accumulate in the queue. Once the problem has abated, we can always spin up extra worker capacity as needed to burn down the queue.

Semi-Homemade Autoscaling
----

Amazon doesn't provide an autoscaling API for DynamoDB. The API for provisioning has a couple of important quirks. You can only increase the provisioning by up to +100% per API call, and another API request to increase will fail until the provisioning change has been completed (presumably this is because Amazon is spinning up DynamoDB instances). You can decrease the provisioning down to 1 read/write unit with a single call, but you are allowed only 2 decreases in provisioning per table per day.

![Nginx requests, intentionally unitless](http://0x74696d.com/slides/images/20130618/daily_nginx_requests.png)

We have a large daily swing in load because "prime time TV" still exists on the web if you have a predominantly North American audience. Because this is a predictable swing in load, we have a cron job that fires off increases and decreases in provisioning. The job fires every 15 minutes. Starting in the early AM it checks if the current throughput is within 80% of provisioned throughput and if so steps up in 20% increments over the course of the day. Using `boto` it's something like the code below.

``` python
ANALYTICS = 'analytics_table'
PROVISIONED = 'ProvisionedThroughput
READ_CAP = 'ReadCapacityUnits'
WRITE_CAP = 'WriteCapacityUnits'

# fill in your connection details here.
# Gotta love that consistent connection API, boto
ddb = boto.connect_dynamodb()
cw = boto.ec2.cloudwatch.CloudWatchConnection()

metric_c = cw.list_metrics('',
                           {'TableName': ANALYTICS},
                           'ConsumedWriteCapacity',
                           'AWS/DynamoDB')
consumed = metric.query(start, end, 'Sum', unit='Count',
                        period=300)[0]['Sum']

if datetime.datetime.now().hour > 6:
    metric_p = cw.list_metrics('',
                               {'TableName': ANALYTICS},
                               'ProvisionedWriteCapacity',
                               'AWS/DynamoDB')[0]
    provisioned = metric_p.query(start, end, 'Sum', unit='Count',
                                 period=300)[0]['Sum']

    ratio = consumed / provisioned
    if ratio > .80:
        provset = {}
        provset[READ_CAP] = ddb.describe_table(ANALYTICS) \
                                              ['Table'] \
                                              [PROVISIONED][READ_CAP]
        provset[WRITE_CAP] = ddb.describe_table(ANALYTICS) \
                                              ['Table'] \
                                              [PROVISIONED][WRITE_CAP]
        provset[pMetric]=threshold*1.2
        table = ddb.get_table(ANALYTICS)
        ddb.update_throughput(table,
                              provset[READ_CAP],
                              provset[WRITE_CAP])
```

I'm eliding a bunch of setup and error-handling code -- check the `boto` docs. We have a similar branch of code that is hit when `now` is in the wee hours of the morning. This branch checks whether the currently used throughput is below a threshold value and steps down our provisioning. Rather than keeping track of state (so we don't use up our 2 decreases), this branch checks the value of the provisioning against a hard-coded value before making the API call.

The very minor risk here is that if we were to somehow have a sudden rush of traffic at 4AM we would get throttled quite a bit, but the SQS queue protects us from this being a serious problem. This solution works for our predictable and relatively smoothly-changing load, but your mileage may vary.


Is DynamoDB the right tool for the job?
----

Between this post, the [slides from the talk](http://0x74796d.com/slides/falling-in-and-out-of-love-with-dynamodb.html), and the earlier discussion of [batch writing]({% post_url 2013-06-05-dynamodb-batch-uploads %}), we've gone over a lot of the interesting properties and gotchas for working with DynamoDB. Some takeaways from my experiences:

- Poor key design == cost & pain
- Batch write with high concurrency to improve throughput
- Use estimation and active monitoring to reduce costs

To figure out if DynamoDB is the right tool for your project, you'll need to look at these three items. And if you're tired of this topic, for my next post we've leave DynamoDB behind for a while.
