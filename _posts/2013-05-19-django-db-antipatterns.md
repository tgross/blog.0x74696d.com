---
layout: post
title: "Django Database Anti-Patterns"
category: Django, performance
---

At work our core application is a big Django project that's been developed over the course of a couple of years.  At the scale at which we're operating, we're finding lots of areas where we've had to tweak or replace out-of-the-box components with more performant alternatives.  One of the areas that's a constant source of pain for me is the Django ORM.

><aside>Disclaimer: I really do like Django.  It's a great tool for getting a site up and running fast. When combined with the typical third-party modules (ex. django-registration, south, etc.), you have that Python-style "batteries included" feel.  But this is a case where a powerful tool makes it easy to cut your finger off.</aside>

Django makes a lot of design choices that make sense in isolation but end up combining into some bad behavior in real production sites.  I'm not going to waste any time second-guessing the authors of Django, but I'll focus on how to work-around or otherwise avoid the painful stuff.

select_related
----

One of the nastiest gotchas in Django is how easy it is to get a `1+n SELECTs` situation. The docs are pretty clear on how to avoid it in view code, but the way that Django's templating system works makes it really easy to suddenly add site-crippling numbers of additional DB queries on a page _with no change to the backend code_.  Observe.

We're using the models from the `books` app from the [Djangobook](https://github.com/jacobian/djangobook.com/blob/master/chapter10.rst).  I've pre-populated my database with with some initial data and I'm running the DB locally with `sqlite3`.  Follow along with [this example code](https://github.com/tgross/tgross.github.io/tree/master/_code/django-db-antipatterns) if you'd like. Here's our minimum `views.py`:
{% highlight python linenos %}
  def get_books_by_date(request, start, end):
      start = dateutil.parser.parse(start)
      end = dateutil.parser.parse(end)
      books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end).order_by('pub_date')
      return render(request, 'template.html', {'books': books, 'start': start, 'end': end})
{% endhighlight %}

And a minimum template to go with it:
{% highlight django linenos %}
  <html><body>
  <h1>Books</h1>
  Published between {{"{{start|date:'Y M d'"}}}} and {{"{{end|date:'Y M d'"}}}}
  <table>
  {{ "{% for book in books "}}%}
  <tr>{{"{{book.title"}}}}: {{"{{book.pub_date"}}}}</tr>
  {{ "{% endfor "}}%}
  </table>
  </body></html>
{% endhighlight %}

If we hit this in a test and check the number of queries, there's no surprises.

{% highlight python linenos %}
  def test_get_books_by_date(self):
      """
      Given a range of dates strings, return books published between
      those dates (inclusive).
      """
      with self.settings(DEBUG=True):
          request = RequestFactory().get('/')
          response = get_books_by_date(request, '2013-05-16', '2013-05-31')
          print len(connection.queries)
          print connection.queries
{% endhighlight %}
We get:
    1
    [{'time': '0.000',
    'sql': u'SELECT "books_book"."id", "books_book"."title",
    "books_book"."publisher_id", "books_book"."pub_date" FROM
    "books_book" WHERE ("books_book"."pub_date" >= 2013-05-16
    AND "books_book"."pub_date" <= 2013-05-31 ) ORDER BY
    "books_book"."pub_date" ASC'}]

One predictable `SELECT` statement made. Now let's do the same thing but with this template:
{% highlight django linenos %}
  <html><body>
  <h1>Books</h1>
  Published between {{"{{start|date:'Y M d'"}}}} and {{"{{end|date:'Y M d'"}}}}
  <table>
  {{ "{% for book in books "}}%}
  <tr>{{"{{book.title"}}}}: {{"{{book.publisher"}}}}, {{"{{book.pub_date"}}}}</tr>
  {{ "{% endfor "}}%}
  </table>
  </body></html>
{% endhighlight %}

Now we get:

    14
    [{'time': '0.000', 'sql': u'SELECT "books_book"."id",
    "books_book"."title", "books_book"."publisher_id",
    "books_book"."pub_date" FROM "books_book" WHERE
    ("books_book"."pub_date" >= 2013-05-16  AND
    "books_book"."pub_date" <= 2013-05-31 ) ORDER BY
    "books_book"."pub_date" ASC'},
    {'time': '0.000', 'sql': u'SELECT "books_publisher"."id",
    "books_publisher"."name", "books_publisher"."address",
    "books_publisher"."city", "books_publisher"."state",
    "books_publisher"."country", "books_publisher"."website"
    FROM "books_publisher" WHERE "books_publisher"."id" = 1 '},
    ...

And on and on, for a total of 13 `SELECT`s on Publisher, one for each of the 13 rows we pulled for Book (and then joined in Python).  Do the math on how much of your response time budget this takes up in your environment, but it's nearly 30% of mine and we haven't done anything except fetch a small set of rows yet. Of course the excellent Django documents point out this problem and that the solution is to use `select_related` so that our view looks like:

{% highlight python linenos %}
 def get_books_by_date(request, start, end):
     start = dateutil.parser.parse(start)
     end = dateutil.parser.parse(end)
     books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
                 .select_related('publisher')\
                 .order_by('pub_date')
     return render(request, 'template.html', {'books': books, 'start': start, 'end': end})
{% endhighlight %}

And this gives us:
    1
    [{'time': '0.000', 'sql': u'SELECT "books_book"."id",
    "books_book"."title", "books_book"."publisher_id",
    "books_book"."pub_date", "books_publisher"."id",
    "books_publisher"."name", "books_publisher"."address",
    "books_publisher"."city", "books_publisher"."state",
    "books_publisher"."country", "books_publisher"."website"
    FROM "books_book" INNER JOIN "books_publisher" ON
    ("books_book"."publisher_id" = "books_publisher"."id")
    WHERE ("books_book"."pub_date" >= 2013-05-16  AND
    "books_book"."pub_date" <= 2013-05-31 ) ORDER BY
    "books_book"."pub_date" ASC'}]

We have a `JOIN`, of course, but not a nasty `1+n` query.

So what's the problem?
----

We're supposed to be working with an "MVT" system.  In a non-trivial application, this query would probably be in a ModelManager method.  Which means when the front-end designer adds a reference to one of our foreign key attributes in the template, our `models.py` file has to change (breaking encapsulation). And unless you factor out a version of the manager method without the `select_related` you're now performing a `JOIN` and `SELECT`ing all the extra fields _everywhere_ the method is called and not just in this one view. The notion expressed in the Django docs that you can have the templating work being done by web designers who aren't versed in Python or the ORM just doesn't hold up. This is a bug farm for performance-related defects.

<img style="margin-left: 15px;" alt="Entire post in one image" src="/images/20130519/DjangoAntiPatternsSummary.png">


Testing (an aside)
----

If you haven't already seen the `connection.queries` call before, it's awfully handy for debugging this sort of thing.  Django provides a bunch of tools to use for query tuning in either the Django shell or your unit tests.

- Check `django.db.connection.queries` to see what queries a test case has executed.
- Check the `query` attribute of Queryset to get the SQL executed by a query.
- Check `_state.db` attribute of an object in a QuerySet to verify multiple DB routing behavior (ex. if you're using a read slave).

Using `connection.queries` requires that you are in DEBUG mode, so if you're running this in your tests you'll need to use a context manager to [override your settings](https://docs.djangoproject.com/en/dev/topics/testing/overview/#overriding-settings). Also, you'll want to make sure you've done a `db.reset_queries()` in your `setUp` method between tests.

Deferred attributes
----

If you have tables with text fields or lots of columns, you'll probably start looking at some point at using the `defer` and `only` methods on querysets. The difference in the SQL generated is that the query `SELECT`s only those columns you're asking for. But this runs into the same problem as not using `select_related`.  Code somewhere else entirely can be modified (perhaps on a different day and by a designer rather than an engineer) and now create a flurry of additional queries.

Now in all fairness the Django documentation calls this out as "advanced usage" and warns against just this problem, but using this feature imposes an additional testing burden above and beyond that of a simple `SELECT` query. If we were using something like an OBDC connection, we'd get an error early in development even with minimal testing.

Many-to-Many Relationships
----

When you have a ManyToMany field, you'll find yourself needing to use `prefetch_related` for most of the same reasons as above.  I've seen this sort of thing lots.

{% highlight django linenos %}
<html><body>
<h1>Books</h1>
Published between {{"{{start|date:'Y M d'"}}}} and {{"{{end|date:'Y M d'"}}}}
<table>
{{ "{% for book in books "}}%}
  <tr>{{"{{book.title}} by
    {{ "{% for author in book.authors.all "}}%}
      {{"{{author.name"}}}}
    {{ "{% endfor "}}%}
    {{"{{book.publisher"}}}},
    {{"{{book.pub_date"}}}}</tr>
{{ "{% endfor "}}%}</table>
</body> </html>
{% endhighlight %}
I'll spare you more SQL output, but using this template with the `select_related` on Publisher but not a `prefetch_related` on Author results in 14 `SELECT`s with lots of `JOIN`s.  So we have to change our view again.

{% highlight python linenos %}
  def get_books_by_date(request, start, end):
      start = dateutil.parser.parse(start)
      end = dateutil.parser.parse(end)
      books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
              .select_related('publisher')\
              .prefetch_related('authors')\
              .order_by('pub_date')
      return render(request, 'template.html', {'books': books, 'start': start, 'end': end})
{% endhighlight %}

This will knock us down to 2 `SELECTS`, one of which uses an `IN` parameter.  The performance on that may not be great either, but it probably beats separate `SELECT`s for each row.  Keep in mind when you do this that you're performing a `JOIN`-equivalent in Python, so you'll want to be aware of how what kind of memory hit you're taking for this operation.

Caching
----

QuerySets are evaluated lazily, and this has a couple of implications for caching.  First, the database isn't hit until you evaluate the queryset in some way -- iterating, slicing with a step, calling `len` or `list` on it, pickling it, etc.  Then it grabs the first 100 rows and will instantiate them as models as they are accessed.  If you are using `memcached` to cache whole querysets, you can easily hit the 1MB slab limit if you are caching a large queryset.  If you go over the limit of your slab size, you'll always get a cache miss, have to fetch the whole queryset, and then get an invalid cache set; you've just made your application perform worse by caching! This means that this sort of thing can be fine when you're working with small datasets but can get out of hand quickly:

{% highlight python linenos %}
  def get_books_by_date(request, start, end):
      cache_key('booksbydate.{}.{}'.format(start, end))
      books = cache.get(cache_key)
      if not books:
          start = dateutil.parser.parse(start)
          end = dateutil.parser.parse(end)
          books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
                  .select_related('publisher')\
                  .prefetch_related('authors')\
                  .order_by('pub_date')
          cache.set(cache_key, books, 60*60)
      return render(request, 'template.html', {'books': books, 'start': start, 'end': end})
{% endhighlight %}

Although if you're not using Paginator on that large queryset, you should probably do that first; your users might rarely go past the first few pages of results anyways and therefore caching the long tail might be worthless.

`django-cache-machine` has an interesting approach to this which is to cache only the models that have actually been evaluated.  So when the CachingQuerySet is hit later, it gets a partially-cached queryset out of cache until it runs out of rows to evaluate, and then does a sliced query back into the database to get the rest you need.  Caching querysets is probably not the best performing approach (`django-cache-machine` creates a _lot_ of cache requests) but so far it's the only approach I've seen to cache invalidation that works well on sites with a good deal of write activity.

Anti-patterns and Solutions
----

The title of this post is probably a slight misnomer.  All the above covers are just some bad technique or failure to read the documentation when taken in isolation.  The anti-patterns are ones in the development process that can get you into trouble:

- Having designers work on templates without knowledge of the underlying view code.
- Having work done on templates treated as unimportant "front-end stuff" that doesn't need code review.
- Adding attribute access on related objects without checking the view or model manager code.
- Caching querysets without knowing how much data you might be putting in there.
- Writing tests for Model collections with only one fixture row for that Model.
- Writing tests for ModelManager methods that don't include a check on the number of queries and/or cache hits made.

It's pretty obvious why Django works this way.  There's nothing magical about attribute access in the templates vs. in view code.  But it reveals a leaky abstraction, and it violates the principle of separation of concerns -- a rich source for defects unless you know what to look for.

><aside>I'm giving a [lightning talk](http://0x74696d.com/slides/django-db-antipatterns.html) based on this post at PhillyPUG's meetup on May 21, 2013.</aside>
