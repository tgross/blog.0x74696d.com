"""
From http://0x74696d.com/posts/tag-all-the-things/
Example of tagging AWS EC2 instances with boto and metaprogramming
Fabric to have dynanmically-generated hostname tasks.

"""

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
                if (role==inst_role and zone=inst_zone and stage=inst_stage):
                    instances.append(instance)
    return instances


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


def tag_all_the_things():
    tag_instances()
    tag_instances('worker')
    tag_instances('admin')
    # etc., add as many as you need here


# ------------------
# dynamic hostname functions

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
