---
layout: post
title: "Session Store Design"
category: security
---

After my talk on DynamoDB a few weeks ago, one of the guys from Basho sent me an email and told me I should check out Riak. So in order to have a project to mess around with it, I decided to work up a session store for Flask. Session stores are one of the use cases called out on Basho's site, so I figured that'd be a good experiment. I'll talk about that project in a later post. Today I want to talk about the session design and about data stores for sessions.

Sessions are an attempt to solve one of the problems around keeping user-associated state in web applications. Because sessions often are used to authenticate users between requests or maintain workflow state, they're a security-sensitive portion of the application better left to framework developers. But most frameworks give you some options and you should understand the tradeoffs. In broad strokes, these options can be divided into client-side and server-side.

Client-side Sessions
----

Client-side sessions leave no state behind on the server and instead put session data into a cookie that is transmitted back and forth between the browser (or other client) and the server. I like to think of this as having the state stored "on the wire." The workflow looks like this:

![client-side sessions workflow](http://0x74696d.com/slides/images/20130627/client-side-sessions.png)

Note that the session has been signed using HMAC to detect tampering. Order of operations is important here. The application framework has to check the HMAC *before* decoding and deserializing the cookie value. Otherwise you're potentially deserializing user-provided data, which I hopefully don't have to tell you is potentially a Very Bad Thing.

Also note that we have the option of encrypting the value of the cookie server-side before encoding it. If you don't, then the session data can be trivially read client-side. Of course, this might be what you want for your application, but you should be aware of it. You can encrypt after serialization to make the cookie entirely unreadable to the client or encrypt selected values in your data structure before serializing it if you want to have a mix of client-readable and non-client-readable data.

The size of stored session data is a potential gotcha. [RFC #2965](http://www.ietf.org/rfc/rfc2965.txt) says that implementations should not limit cookie sizes, but in practice browsers and web servers do. From what I can find browsers typically limit to 4093 bytes per domain. Web servers have their own limits that can be individually configured; on Nginx this limit includes the entire client header (see [large_client_header_buffers](http://wiki.nginx.org/HttpCoreModule#large_client_header_buffers) in the Nginx docs). Remember to include the size of your HMAC signature and delimiter in the cookie size -- that's going to be 40 bytes for a SHA-1 and 64 bytes for a SHA-256 signature. I suggest not trying to cut it close on the cookie size.

One of the major advantages of this approach, and why [we](http://www.dramafever.com) use it is because it doesn't require database writes. If you're frequently updating session data and that data isn't sensitive, this might be a good approach.

Several of the popular Python web frameworks give you this option. Flask is currently shipping with the `itsdangerous` plugin. You can turn on cookie-backed sessions in Django by setting `SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"`. I hear Pylons ships with `beaker` (I haven't looked at this in detail, so I don't know how good it is). If you're looking at some other framework's options, you want to make sure the author is signing the cookie with HMAC and not some other half-assed hash mechanism. Make sure the secret key you use for signing isn't accessible by anyone other than your web process -- hardening keys for web apps is worth a post all on its own.

Other than session data size and letting the client read unencrypted session data, another potential problem with client-side sessions is that they're racy. Suppose your application has several Ajax calls on a single web page. Ajax call #1 is fired, then Ajax call #2 is fired. But variable latency means that call #2 returns first, and let's further suppose the session has been modified. When call #1 returns immediately thereafter, it overwrites the session values set in call #2. For many applications this isn't going to be a deal-breaker; if you don't make async calls that modify the cookie you have nothing to worry about.


Server-side Sessions
----

If you want to store large chunks of data or don't want to encrypt session data, you'll want to use server-side sessions. This means we pass the client a cookie with a session identifier and then use that ID to lookup the session data from some kind of data store. This workflow is less complex and looks like this:

![server-side sessions workflow](http://0x74696d.com/slides/images/20130627/server-side-sessions.png)

Server side sessions are easier to get right from a security perspective. As long as you have a hard-to-spoof session token you're in pretty good shape (but see the notes about HTTP-only and SSL below). If you want to go crazy, you can finger-print the client and then use that and your secret key to sign the session token to reduce the risk of session stealing. In practice if you do that you'll end up logging people out and losing sessions more often than you might intend -- browser fingerprints change a lot.

The backing datastore for your sessions can be just about anything, but you'll want to select one based on your needs for latency, availability, and consistency. Low-latency is fairly critical as you get more users. If you're building something like a startup with an intent for explosive growth, keep in mind that if you're using something like MySQL that the table is going to be appended-to frequently and have a lot of updates. (Your product designers are going to want to stick all kinds of data in the session.) This is going to impact latency to a point where availability might be compromised. Redis is popular for sessions because it combines high speed -- everything is in RAM -- with the ability to shard easily and back it off to disk for persistence. If you don't care about persistence at all, memcached can work.

The mini-project I discussed in the intro uses Riak as a session store for Flask so that I can compare it against using DynamoDB and play around with its cool operations tools. The problem both of these stores have is lack of consistency; this might not be a problem for a given application but if it isn't one might want to go with client-side sessions anyways. You can tune Riak to be more consistent by manipulating the `r`/`w` variables, but naturally this is going to reduce availability. (I suspect but haven't confirmed that it will increase latency slightly as well.)

Most of the popular Python web frameworks give you the option for server-side sessions too. In Django it's the default session engine. CherryPy gives only this option. For Flask you'll need to write your own or select one already written like [this one](http://flask.pocoo.org/snippets/75/) for Redis-backed sessions that I used as inspiration for the `flask-riak-sessions` project I'm working on. Note that snippet uses `pickle`, which I don't recommend as a serializer for sessions because I'm paranoid. It's too easy to screw up and put unsanitized data into the session store and have it deserialized into arbitrary Python code that will pwn your server.


Securing Sessions on the Wire
----

Both server-side and client-side sessions use cookies to maintain state. If a cookie is spoofed, the attacker can act as if he were the legitimate client. There are a couple of mechanisms you as an application designer can use to harden cookies during transmission -- but if the user's browser is compromised then all bets are off.

First is to set the [HttpOnly](http://tools.ietf.org/html/rfc6265#section-5.2.6) flag at the server. If you do a search on this flag, there's a pretty good chance you're going to end up at [this](http://stackoverflow.com/questions/27972/how-do-httponly-cookies-work-with-ajax-requests) StackOverflow discussion which has some dated information so beware. The purpose of HttpOnly is to prevent client-side scripts from manipulating cookies. Cookies set by the server are still returned by Ajax calls from the client, so you can use HttpOnly cookies for authenticated Ajax APIs for server-side sessions. If you intend for the client to access the cookie then you don't want to set HttpOnly.

The other protection is to use SSL for authenticated sessions, and not just during login. This prevents sniffing the cookie in transit. There's an obvious cost impact for having everything under SSL; if you're using a CDN in front of your application this cost can be quite high.


tl;dr
----

There isn't really a don't-make-me-think-version of this post. You should almost certainly be using the HttpOnly flag and putting your whole site under SSL for authenticated users. If you have any question as to whether you will be putting sensitive data in the session or how to encrypt that data safely, you should be using a server-backed session. Redis is a great backing store for server-backed sessions. Client-side sessions have their place, but there are plenty of fairly bad client-side session implementations out there so do your research.
