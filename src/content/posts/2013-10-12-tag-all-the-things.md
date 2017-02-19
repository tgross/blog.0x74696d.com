---
categories:
- AWS
date: 2013-10-12T00:00:00Z
title: Tag All The Things!
slug: tag-all-the-things
---

If you're using push-based orchestration like Fabric, you need hostnames to send commands over `ssh` to your instances. But if the instances are in an AWS autoscaling group, you don't know most of the hostnames of the boxes at any given time. Typing out EC2 hostnames like `ec2-11-222-33-44.compute-1.amazonaws.com` sucks once you have a couple dozen instances in play. You could have each box register itself in Route53 with some kind of friendly name, but then you'll need to wait for DNS propagation and your local `~/.ssh/known_hosts` file is going to be out-of-date if you reuse names.

><aside>Of course you can get around this problem with pull-based orchestration like Puppet. But now you have a client on each box that needs some kind of credentials for the control host. That control host needs to be highly-available. In practice, I use a mix of pull-based and push-based orchestration, but I'll deal with this larger philosophical debate in another post some other day.</aside>

There's a two-part solution to this that makes both orchestration and plain old shelling into a remote host easier and faster.

Tag All The Things!
----

The first part is to use AWS tags to uniquely name each EC2 instance. Instances in an autoscaling group all have the tag `aws:autoscaling:groupName` automatically added. If our group names are well-structured, we can use them to tag individual instances with a unique and predictable `Name` tag.

First we'll use the Python `boto` library to get all the instances we're interested in. Put this in your Fabfile. Later we'll call this function from a task that puts this all together.

~~~ python
AUTOSCALE_TAG = 'aws:autoscaling:groupName'

def get_instances(role=None, zone=None, stage='prod'):
    """
    Get EC2 instances for a given functional role, AWS availability
    zone, and deployment stage. Ex. instances in group "web-prod-1a"
    """
    conn = boto.ec2.get_region(region).connect()
    instances = []
    for reservation in conn.get_all_instances():
        for inst in reservation.instances:
            # we only want autoscaling instances, and not ones that
            # are being terminated (no public_dns_name)
            group = instance.tags.get(AUTOSCALE_TAG, False)
            if group and instance.public_dns_name:
                inst_role, inst_stage, inst_zone = group.split('-')
                if (role==inst_role and zone=inst_zone and
                      stage=inst_stage):
                    instances.append(instance)
    return instances
~~~

This is a de-factored version of what I actually run; normally much of this is factored away into a common library of code we use for AWS management. This version also leaves off handling of user input errors for clarity and brevity (as usual). It should be clear what we're doing for naming conventions. We have instances grouped into "roles" like "web", "worker", or code names for internal-facing services, etc. We split them across AWS availability zones, and we can handle multiple stages with the same function (i.e. "prod", "staging", "test", etc.), although we normally run all non-production instances under a different AWS account.

This function gets called by a task that does the actual tagging:

~~~ python

def tag_instances(role='web', stage='prod'):
    """
    Tags all instances for a given role across all AZ.
    """
    for zone in ('1a', '1b', '1c', '1d', '1e'):
        hosts_in_zone = get_instances(role=role, zone=zone, stage=stage)

        # construct a base for the name tag
        zone_map = {'1a': '0', '1b': '1', '1c': '2', '1d': '3', '1e': '4'}
        base_name = '{}{}'.format(zone, zone_map[zone])
        used_names = {}

        # find the unnamed instances and name them; we can't rely on
        # order of tags coming back so we loop over them twice.
        unnamed_hosts = []
        for host in hosts_in_zone:
            name = host.tags.get('Name', '')
            if name:
                used_names[name] = host
            else:
                print('Found unnamed host {}'.format(host))
                unnamed_hosts.append(host)
        for host in unnamed_hosts:
            i = 1
            # find the next open name and assign it to the host
            while True:
                # use whatever padding you need here
                hostname = '{}{:02}'.format(base_name, str(i))
                if hostname not in used_names:
                    print('Tagging {}'.format(hostname))
                    host.add_tag('Name', hostname)
                    used_names[hostname] = host
                    break
                else:
                    i += 1
~~~

This algorithm isn't particularly efficient. But the `boto` API doesn't guarantee any sort of ordering, and we don't know if the array of names is sparse at runtime (for example, what if we had to terminate an instance that went belly-up?). Our total number of instances isn't particularly large, so this is acceptably bad.

We can then take this function and wrap it in a Fabric task for all our known roles.

~~~ python
def tag_all_the_things():
    tag_instances()
    tag_instances('worker')
    tag_instances('admin')
    # etc., add as many as you need here
~~~

So before we start a session of work we can go `fab tag_all_the_things` and know that all our currently-running and available EC2 instances will be name-tagged like we can see in the console below:

![tagged instance](/images/20131012/tags.png)

If you do this, you'll probably want to write some code that queries the current tags, autoscaling groups, and/or load balancers and displays their status. We wrap these in Fabric tasks so we can use one interface for `boto`, the [AWS CLI](http://aws.amazon.com/cli/), or shelling out to the older AWS command line tools where we haven't got around to porting them. So I can check on the status of a load balancer and what instances are tagged in it with `fab pool_show:web`, for example.

One warning here. I have it on good authority from an AWS operations guru [Jeff Horwitz](http://engineering.monetate.com/2012/11/01/devops-monetate-etsy/) that tagging can, very rarely, fail or act as though eventually-consistent. I have yet to see it but he runs a much larger operation and describes it as baffling if you're not at least aware it was possible.

Metaprogramming Fabric
----

So now we have our instances all tagged at any time. Big deal, how do we use that? This is where things get hacky. In my Fabfile, I generate a mapping of names to EC2 public DNS names at runtime, and then dynamically generate a named Python function that adds the appropriate host to the Fabric execution environment.

In other words, instead of doing:

`fab -H ec2-11-222-33-44.compute-1.amazonaws.com dostuff`

I can do:

`fab web001 dostuff`

~~~ python
# get a reference to the fabfile module
this = __import__(__name__)
all_hosts = {}

# create a function
def _set_host_factory(name):
    return lambda: _set_host(name)

def _set_host(name):
    env.hosts = [all_hosts[name],]
    env.host_name = name

# note: this loop is in the module namespace, not a function
for host in get_instances():
    tag = host.tags.get('Name')
    host_name = host.public_dns_name
    if host_name:
        all_hosts[tag] = host_name
        # bind our function to a name at the module level
        setattr(this, tag, _set_host_factory(tag))
~~~

In this same section we could add code that adds the hosts to the Fabric roledefs as well. And if we'd prefer, we could have the `_set_host` function append to the Fabric `env.hosts` instead of replacing it. That would let us run more than one hostname in the fab command (ex. `fab web001 web002 dostuff`). But if I'm pushing tasks up to multiple hosts I usually like to do it by roledef or looping over the hosts so that I can more easily follow the progress of the task. Your mileage may vary.

Stupid Pet Tricks with SSH Config Files
----

The last part to add here is that sometimes we like to be able to `ssh` into a given EC2 instance if it's behaving abnormally. To this end I (ab)use my ssh config file. My `~/.ssh` directory looks like this:

~~~
tgross@Durandal:~$ ll ~/.ssh
total 136
-rw-r--r--  1 tgross  staff   3.9K Oct 11 21:37 config
-rw-r--r--  1 tgross  staff    45K Oct 10 13:02 known_hosts
drwxr-xr-x  2 tgross  staff    68B Oct 12 11:36 multi
-rw-r--r--  1 tgross  staff   531B Jul  7 12:37 my_config
-rwxr-xr-x  1 tgross  staff   126B Jul  6 12:25 ssh_alias.bash
-rw-------  1 tgross  staff   1.6K Jul  6 18:12 tgross
-rw-r--r--  1 tgross  staff   400B Jul  6 18:12 tgross.pub
~~~

I've got a `my_config` file that contains everything you'd usually find in a ssh config file. Then in my `~/.bash_profile` I've got the following:

~~~ bash
# gets hostnames provided by the fab script
alias update-ssh='cat ~/.ssh/my_config $FABFILEPATH/ssh_host.config > ~/.ssh/config'
update-ssh
~~~

Where `$FABFILEPATH` is the directory where my Fabfile lives. This means that every time I fire up a shell or use the command alias `update-ssh`, I'm replacing my `~/.ssh/config` file with the combination of my personal configuration and some file that lives in the `$FABFILEPATH`. So where does this file come from? We can create it from our Fabfile by modifying the code we saw above like so:

~~~ python
# get a reference to the fabfile module
this = __import__(__name__)
all_hosts = {}

# create a function
def _set_host_factory(name):
    return lambda: _set_host(name)

def _set_host(name):
    env.hosts = [all_hosts[name],]
    env.host_name = name

f = open('./ssh_host.config', 'w')

# note: this loop is in the module namespace, not a function
for host in get_instances():
    tag = host.tags.get('Name')
    host_name = host.public_dns_name
    if host_name:
        all_hosts[tag] = host_name
        # bind our function to a name at the module level
        setattr(this, tag, _set_host_factory(tag))
        f.write('Host {}\nHostname {}\nUser ubuntu\n\n'.format(tag, host_name))

f.close()
~~~

We've added code to write out host aliases and hostnames to the `ssh_host.config` file that we'll concatenate into our `~/.ssh/config` file. This lets me access any instance just by going `ssh web001`.

Another nice advantage of this is that it avoids name collisions in `~/.ssh/known_hosts`. So if I scale up to 10 "web" instances in an availability zone and have a "web010", and if that instance is terminated by scaling down later, the next time I see a "web010" I won't have to worry about editing my `~/.ssh/known_hosts` file to remove the old entry. You will accumulate a lot of cruft there, though, so you should probably have a job run through and clean yours out from time-to-time. I just do a quickie `C-SPC M-> C-w` now and then, but if you have a much larger installed base that might not do the job.

><aside>Download the code from this post <a href="https://github.com/tgross/tgross.github.io/tree/master/_code/tag-all-the-things.py">here</a></aside>
