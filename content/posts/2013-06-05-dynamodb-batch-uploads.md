---
categories:
- AWS
- DynamoDB
date: 2013-06-05T00:00:00Z
title: DynamoDB Batch Uploads
slug: dynamodb-batch-uploads
---

I work with a moderately large AWS deployment, and this includes a few applications that are using Amazon's DynamoDB. One of the many many quirks of working with DynamoDB is that it's optimized towards highly parallel operations. Ordinarily this is exactly what you want, but if you ran into the situation I did over the weekend not so much.

I had a modestly-sized data subset of user video-watching habits &mdash; on the order of 10s of millions of rows &mdash; that had to be transfered from a MySQL instance on RDS to DynamoDB. Obviously when going from a relational store to a non-relational one, there also needed to be a transformation of that data. The data had to be duplicated to three different tables because of an idiosyncratic schema optimized towards fast reads. (Actually, more like idiomatic &mdash; I'm speaking at [PhillyDB](http://www.meetup.com/phillydb/) this month on DynamoDB if you're interested in learning more about DynamoDB schema design, operations, etc.) And due to what was honestly some poor decision-making on my part, I needed it done in a hurry.

I already had code that would be writing new records to the table later down the road when the system went to production, so I figured I'd just make a query against RDS, page the results in chunks of a couple hundred, do the transformations, and then use the [boto](http://boto.readthedocs.org/en/latest/dynamodb_tut.html)-based code to do the uploads. No problem, right?  Except that of course when I tried that I was maxing out at about 100 writes/second, which was going to take way more time than I had. I wanted at least 1000/sec, and more if I wanted to make it to beer o'clock before the weekend was over.

At this point I checked that I hadn't made a bone-headed key distribution mistake that would throttle me down to a tenth of my provisioned throughput, and I switched to the `batch_write` API (this I should have done in the first place, but I was going for laziness) and fiddled with my query page size.  I could still only get up to about 200 writes/second this way.

Time to get hacky.

The first step was to take the query and data transformation out of the loop and avoid doing the work on a constrained-in-every-way EC2 instance. I grabbed the RDS table with `mysqldump` and brought it to my laptop.  Armed with `sed`, `cut`, and `sort`, I managed to get the table into the shape I wanted it after about an hour, resulting in three big ol' CSV files something like the one below.

    user,    series, episode, timestamp, moddt
    1234567, 123,    1,       60,        2013-06-05T10:00:00

Timestamp in this case is position within the video. And DynamoDB only takes strings and numbers, so there's no good way to dates represented which is how you end up with ISO-format date strings.

Next I needed to be able to generate a lot of simultaneous parallel requests in order to hit the throughput I wanted. I have a production system using `gevent` that can process 1000+ writes/sec to DynamoDB per core before it has its coffee in the morning, but it's specialized for its task and again, I was in a hurry. And even with that system I'd previously ran into throughput problems due to GIL contention, so multiprocessing was the way to go.

``` python
import csv
import boto
from multiprocessing import Pool


def write_data(filename):
   """
   This will be called by __main__ for each process in our Pool.
   Error handling and logging of results elided.
   Don't write production code like this!
   """
   conn = boto.connect_dynamodb(aws_access_key_id=MY_ID,
                         aws_secret_access_key=MY_SECRET)
   table = conn.get_table('my_table_name')

   with open(filename, 'rb') as f:
      reader = csv.reader(f)
      items = []
      for row in reader:
         dyn_row = table.new_item(hash_key='{}',format(row[0]),
                                  attrs = {'series': row[1],
                                           'episode': row[2],
                                           'timestamp': row[3],
                                           'moddt': row[4] })
         items.append(dyn_row)

```

Now, you could stop here and just `batch_write` things up to DynamoDB and that will work if you're writing a couple thousand rows. But it should be obvious we're going to blow up memory on our laptop if we try that.

``` python
      if len(items) == 25:
         batch_list = conn.new_batch_write_list()
         batch_list.add_batch(table, items)
         response = conn.batch_write_item(batch_list)
         items = []
```

Okay, so we'll treat our list as a queue, and when it gets to the maximum size we can push in a single batch write, we'll push that up. But I buried the problem with this when I elided the error handling &mdash; if the write is throttled by DynamoDB, you'll be silently dropping writes because `boto` doesn't raise an exception. So let's try that part again.

``` python
      if len(items) > 25:
         batch_items = items[:25]
         batch_list = conn.new_batch_write_list()
         batch_list.add_batch(table, batch_items)
         response = conn.batch_write_item(batch_list)
         if not response['UnprocessedItems']:
            items = items[25:]
         else:
            unprocessed = [
                           ui['PutRequest']['Item']['user']
                           for ui in
                           response['UnprocessedItems']['my_table_name']
                           ]
            for item in batch_items:
               if item['user'] not in unprocessed:
                  items.remove(item)
```

On every `batch_write` request we take out what we've successfully written and retry everything else in the next pass. Yes, we're doing a *lot* of allocation with the list, but there's a reason for it. We're almost certain to get throttled by DynamoDB in a batch upload unless we massively over-provision.  This function minimizes the number of requests we make while constraining the length of the list. I modeled this and throttling would have to reach consistent double-digit percentages of unprocessed writes before we'd see significant loss of throughput or runaway memory usage.

``` python
if __name__ == '__main__':
    files = ['xaao','xabf','xabw',... ]
    pool = Pool(processes=len(files))
    pool.map(write_data, files)
```

Last we use our multiprocessing pool to split the job over a large number of processes. I used `split -a 3 -l 300000` to split my big CSVs into a couple hundred files. With no shared memory between the processes, I can use the non-thread-safe code above without worry. This let me crank through all the input files within a few hours and I was ready for beer o'clock.

><aside>Download this example code <a href="https://github.com/tgross/blog.0x74696d.com/blob/trunk/static/_code/dynamodb-batch-uploads/batch_upload.py">here</a></aside>
