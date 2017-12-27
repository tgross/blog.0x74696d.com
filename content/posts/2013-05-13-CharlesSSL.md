---
categories:
- security
date: 2013-05-13T00:00:00Z
title: Securing Charles Proxy with a Personal CA
slug: charlesssl
---

Some of the guys in my shop like to use [Charles](http://www.charlesproxy.com) proxy to help debug their web and mobile applications. It's no good for non-HTTP traffic so it's a bit of a unitasker, but modulo some questionable UI choices it's not bad.  Charles is user-friendly enough that you can hand it off to a wet-behind-the-ears web developer who wouldn't know a TCP SYN flag if you waved it at him.  And it has some nice features like on-the-fly traffic throttling that we find handy in the online video business -- as far as I know you can't do that with [Burp suite](http://portswigger.net/burp/).

But Charles has one head-scratcher, and that's proxying SSL traffic.  The author gives instructions to [install the Charles certificate](http://www.charlesproxy.com/documentation/using-charles/ssl-certificates/) as a trusted root, but this is a _really_ bad idea.  Anyone can download that certificate and key and use it to sign certificates in the same way Charles does.  Which means if you set the Charles certificate as trusted root, you're one DNS spoof or spearphishing attack away from handing over your credentials to arbitrary secure sites to the owner of some sketchy `.ru` domain.

What you _should_ do (and what the [author](http://blog.xk72.com/) of Charles should recommend) is to set up your own certificate authority (CA) and trust that instead.  We can use this for more than just Charles, but I'll touch on that at the end of this post.  The whole process is barely more complicated than generating the X.509 self-signed cert you might be using for your home web server anyways.  The instructions below work on my OS X development machine but should be the same for any Unixy machine with OpenSSL installed.

We're going to build our new CA in `/usr/local`, and OpenSSL on my machine was built so that its configuration file was stored in `/opt/local/etc/openssl/openssl.cnf`.  Yeah, yeah, we can get religious about the Unix FHS some other time.  Let's get our environment prepped:

``` bash
mkdir -p /usr/local/CharlesCA
cd /usr/local/CharlesCA
mkdir certs private newcerts
echo 01 > serial
touch index.txt
```

On the last two items: `serial` contains the next serial number that will be assigned to a cert, in hex.  The `index.txt` file is the text database of issued certificates.  Next we create the certificate and key used for our new CA.


``` bash
openssl req -new -x509 -days 3650 -extensions v3_ca \
            -keyout private/ca_key.pem -out certs/ca_cert.pem \
            -config /opt/local/etc/openssl/openssl.cnf
```

Ok, what are we doing here?  We're making a new X.509 certificate request with the appropriate extension to use the certificate for signing other certificates (or in other words, use it as a CA).  We're going to give it a very long expiration period because we're lazy and want to guarantee we won't have to do this again on this machine.  And we're outputting both a private keyfile (`ca_key.pem`) and the public certificate file (`ca_cert.pem`). If you're following along, you'll get something like the below.  Fill in your information.

```
Generating a 1024 bit RSA private key
...++++++
........................................++++++
writing new private key to private/ca_key.pem
Enter PEM pass phrase:
Verifying - Enter PEM pass phrase:
-----
You are about to be asked to enter information that will be
incorporated into your certificate request.
What you are about to enter is what is called a Distinguished Name
or a DN. There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter ., the field will be left blank.
-----
Country Name (2 letter code) [AU]:US
State or Province Name (full name) [Some-State]:Pennsylvania
Locality Name (eg, city) []:Philadelphia
Organization Name (eg, company) [Internet Widgets Pty Ltd]:
Organizational Unit Name (eg, section) []:
Common Name (e.g. server FQDN or YOUR name) []:0x74696d.com
Email Address []:tim@0x74696d.com
```

We've got our CA now, and if we trust it as a root authority (we'll get to that in a minute), we can create SSL certificates that our browser will accept without complaint.  But Charles expects the signing certificate to be in PKCS12 format.  So we need to use OpenSSL again to convert our keys to a .pfx file.

``` bash
openssl pkcs12 -export -out ca_cert.pfx -inkey private/ca_key.pem \
               -in certs/ca_cert.pem
```


><aside>Update 2013/10/12: Thanks to <a href="https://twitter.com/markaufflick">Mark Aufflick</a> who pointed out I was missing the certs directory path from the "-in" argument of this command</aside>

The `ca_cert.pfx` output file for this is what we'll add as a trusted root cert.  On OS X the easiest way to do this is just to hit the directory in Finder and double-click the cert (you can also use the `security` command-line interface).  Keychain Access will come up and ask you if you're really really sure, that you're aware that you are granting this cert the right to make arbitrary Facebook posts about your mother-in-law on your behalf, etc.

![Do you want to trust certificates signed by 0x74696d.com?](/images/20130513/1.png)

You should see the following when you're done.

![This certificate is marked as trusted](/images/20130513/2.png)

Now we can fire up Charles and configure it to use our new certificate.  Under Proxy Settings and the SSL tab, check _Use a Custom CA Certificate_.  For some reason on my installation, the Choose button would not find `/usr/local` at all so I had to enter the path by hand.  We'll trust this for all locations.

><aside>Update 2013/10/12: Thanks to <a href="https://twitter.com/markaufflick">Mark Aufflick</a> who pointed out you can just drag the .pfx file into the dialog.</aside>

![Proxy settings](/images/20130513/3.png)

And now we can go visit our favorite SSL-secured sites and sniff the exchange.

![Sniffing Github traffic](/images/20130513/4.png)

You can use this same CA to sign what would otherwise be snake-oil certs for your development environment so that you don't have to shell out for an SSL certificate. But I like to use a separate CA for that -- each machine I use for development can have its own CA generating temporary certs like those used by Charles, and I can have a separate one for signing certificates I want to use across multiple machines. This also makes revocation easier if you lose a machine to theft.

The machine with the private key for that CA is an internally-facing server and not something like a laptop that you'll carry into high-risk environments like an open WiFi at LAS during DEFCON.  Or ideally, you should remove the CA entirely from your machine once you've created certificates with it, and leave the private key burned to a CD so you can recreate the CA and renew the certificates when necessary. This way the key can't be compromised without the theft of the CD backup.
