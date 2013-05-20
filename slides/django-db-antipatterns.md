# Django Database<br/>Anti-Patterns

<div style="position: absolute; bottom: 0">
<p>tim gross | @0x74696d</p>
<p>http://0x74696d.com/posts/django-db-antipatterns/</p>
</div>

---

![Summary](http://0x74696d.com/images/20130519/DjangoAntiPatternsSummary.png)

---

# 1+n queries

Minimal view:

    !python
    def get_books_by_date(request, start, end):
       start = dateutil.parser.parse(start)
       end = dateutil.parser.parse(end)
       books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
                           .order_by('pub_date')
       return render(request, 'template.html',
                    {'books': books, 'start': start, 'end': end})

<br/>
Minimal template:

    !django
    <html><body>
    <h1>Books</h1>
    Published between {{start|date:"Y M d"}} and {{end|date:"Y M d"}}
    <table>
    {% for book in books %}
    <tr>{{book.title}}: {{book.pub_date}}</tr>
    {% endfor %}</table>
    </body> </html>

.notes: Really easy for template code to produce a `1+n SELECTs` situation.

---

# 1+n queries

Run this:

    !python
    def test_get_books_by_date(self):
       """
       Given a range of dates strings, return books published between
       those dates (inclusive).
       """
       with self.settings(DEBUG=True):
           request = RequestFactory().get('/')
           resp = get_books_by_date(request, '2013-05-16', '2013-05-31')
           print '{} SELECT(s)\n-------'.format(len(connection.queries))
           print connection.queries

We get:

    1 SELECT(s)
    -------
    [{'time': '0.000',
    'sql': u'SELECT "books_book"."id", "books_book"."title",
    "books_book"."publisher_id", "books_book"."pub_date" FROM "books_book"
    WHERE ("books_book"."pub_date" >= 2013-05-16 AND "books_book"."pub_date"
    <= 2013-05-31 ) ORDER BY "books_book"."pub_date" ASC'}]

---

# 1+n queries

Change the template to:

    !django
    <html><body>
    <h1>Books</h1>
    Published between {{start|date:"Y M d"}} and {{end|date:"Y M d"}}
    <table>
    {% for book in books %}
    <tr>{{book.title}}: {{book.publisher}}, {{book.pub_date}}</tr>
    {% endfor %}</table>
    </body> </html>

---

# 1+n queries

Now we get:

     14 SELECT(s)
    -------
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
    {'time': '0.000', 'sql': u'SELECT "books_publisher"."id",
    "books_publisher"."name", "books_publisher"."address",
    "books_publisher"."city", "books_publisher"."state",
    "books_publisher"."country", "books_publisher"."website"
    FROM "books_publisher" WHERE "books_publisher"."id" = 2 '},
    {'time': '0.000', 'sql': u'SELECT "books_publisher"."id",
    "books_publisher"."name", "books_publisher"."address",
    "books_publisher"."city", "books_publisher"."state",
    "books_publisher"."country", "books_publisher"."website"
    FROM "books_publisher" WHERE "books_publisher"."id" = 3 '},
    ...

---

# 1+n queries

    !python
    def get_books_by_date(request, start, end):
       start = dateutil.parser.parse(start)
       end = dateutil.parser.parse(end)
       books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
                           .order_by('pub_date')
                           .select_related('publisher')
       return render(request, 'template.html',
                    {'books': books, 'start': start, 'end': end})

.notes: In a non-trivial application, this query would probably be in a ModelManager method.  Which means when the front-end designer adds a reference to one of our foreign key attributes in the template, our `models.py` file has to change (breaking encapsulation).

---

# 1+n queries

And this gives us:

    1 SELECT(s)
    -------
    [{'time': '0.000',
    'sql': u'SELECT "books_book"."id", "books_book"."title",
    "books_book"."publisher_id", "books_book"."pub_date",
    "books_publisher"."id", "books_publisher"."name",
    "books_publisher"."address", "books_publisher"."city",
    "books_publisher"."state", "books_publisher"."country",
    "books_publisher"."website"
    FROM "books_book"
    INNER JOIN "books_publisher"
    ON ("books_book"."publisher_id" = "books_publisher"."id")
    WHERE ("books_book"."pub_date" >= 2013-05-16  AND
    "books_book"."pub_date" <= 2013-05-31 )
    ORDER BY "books_book"."pub_date" ASC'}]

---

# So what?<br/>RTFM, right?

---

# MVT but no separation of concerns

- ## Change template.html --> change models.py ##

- ## Now all callers of your ModelManager methods have extra JOINs they didn't need. ##

- ## Can't have template work done by designers who aren't versed in Django ORM. ##

- ## Reliable source of performance-related defects. ##

.notes:  Unless you factor out a version of the manager method without the `select_related` you're now performing a `JOIN` and `SELECT`ing all the extra fields _everywhere_ the method is called and not just in this one view.

---


# many-to-many relationships

To do this:

    !django
    <html><body>
    <h1>Books</h1>
    Published between {{start|date:'Y M d'}} and {{end|date:'Y M d'}}
    <table>
    {% for book in books %}
      <tr>{{book.title}} by
        {% for author in book.authors.all %}
          {{author.name}}
        {% endfor %}
        {{book.publisher}},
        {{book.pub_date}}</tr>
    {% endfor %}</table>
    </body> </html>

---

# many-to-many relationships

You need this:

    !python
    def get_books_by_date(request, start, end):
       start = dateutil.parser.parse(start)
       end = dateutil.parser.parse(end)
       books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
               .select_related('publisher')\
               .prefetch_related('authors')\
               .order_by('pub_date')
       return render(request, 'template.html',
                    {'books': books, 'start': start, 'end': end})

.notes: This will knock us down to 2 `SELECTS`, one of which uses an `IN` parameter.  The performance on that may not be great either, but it probably beats separate `SELECT`s for each row.  Keep in mind when you do this that you're performing a `JOIN`-equivalent in Python, so you'll want to be aware of how what kind of memory hit you're taking for this operation.

---

# deferred attributes

You can avoid `SELECT`ing on every column by using `only` and `defer`.

    !python
    def get_publishers_by_state(request, state):
       publishers = Publisher.objects.filter(state=state).\
                             .defer('address', 'city', 'country')
       return render(request, 'template.html',
                     {'publishers': publishers})

Results in:

    [{'time': '0.001',
    'sql': u'SELECT "books_publisher"."id", "books_publisher"."name",
    "books_publisher"."state", "books_publisher"."website"
    FROM "books_publisher" WHERE "books_publisher"."state" = New York'}]

<br/>
But you get 1+n again if you access one of the deferred columns!

---

# Testing

Django provides tools for query tuning in the Django shell or unit tests.

<br/>

- Check `django.db.connection.queries` to see what queries a test case has executed.
- Check the `query` attribute of Queryset to get the SQL executed by a query.
- Check `_state.db` attribute of an object in a QuerySet to verify multiple DB routing behavior (ex. if you're using a read slave).

Using `connection.queries` requires that you are in DEBUG mode, so if you're running this in your tests you'll need to use a context manager to override your settings.

Do a `db.reset_queries()` in your `setUp` method between tests.

---

# Anti-patterns

The anti-patterns are those in the development process:<br/>

- Having designers work on templates without knowledge of the underlying view code.
- Having work done on templates treated as unimportant "front-end stuff" that doesn't need code review.
- Adding attribute access on related objects without checking the view or model manager code.
- Writing tests for Model collections with only one fixture row for that Model.
- Writing tests for ModelManager methods that don't include a check on the number of queries and/or cache hits made.

.notes: It's pretty obvious why Django works this way.  There's nothing magical about attribute access in the templates vs. in view code.  But it reveals a leaky abstraction, and it violates the principle of separation of concerns -- a rich source for defects unless you know what to look for.

---

# Django Database<br/>Anti-Patterns

<div style="position: absolute; bottom: 0">
<p>tim gross | @0x74696d</p>
<p>http://0x74696d.com/posts/django-db-antipatterns/</p>
</div>
