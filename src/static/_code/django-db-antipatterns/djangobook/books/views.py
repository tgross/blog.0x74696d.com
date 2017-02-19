"""
Example views for accessing the database, some of which are not good approaches.
"""

import dateutil.parser
from django.core.cache import cache
from django.shortcuts import render

from books.models import Book

def get_books_by_date(request, start, end):
    """
    Minimum books_by_date view.
    """
    start = dateutil.parser.parse(start)
    end = dateutil.parser.parse(end)
    books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end).order_by('pub_date')
    return render(request, 'template1.html', {'books': books, 'start': start, 'end': end})

def get_books_by_date_bad(request, start, end):
    """
    books_by_date view with a template that accesses un-queried foreign key references.
    """
    start = dateutil.parser.parse(start)
    end = dateutil.parser.parse(end)
    books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end).order_by('pub_date')
    return render(request, 'template2.html', {'books': books, 'start': start, 'end': end})

def get_books_by_date_good(request, start, end):
    """
    books_by_date view with a template that accesses un-queried foreign key references,
    this time with a select_related to avoid the additional queries.
    """
    start = dateutil.parser.parse(start)
    end = dateutil.parser.parse(end)
    books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
            .select_related('publisher')\
            .order_by('pub_date')
    return render(request, 'template2.html', {'books': books, 'start': start, 'end': end})

def get_books_by_date_with_author_bad(request, start, end):
    """
    books_by_date with authors view with a template that accesses un-queried many-to-many
    references.
    """
    start = dateutil.parser.parse(start)
    end = dateutil.parser.parse(end)
    books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
            .select_related('publisher')\
            .order_by('pub_date')
    return render(request, 'template3.html', {'books': books, 'start': start, 'end': end})

def get_books_by_date_with_author_good(request, start, end):
    """
    books_by_date with authors view with a template that accesses un-queried many-to-many
    references, this time with a prefetch_related to avoid the additional queries.
    """
    start = dateutil.parser.parse(start)
    end = dateutil.parser.parse(end)
    books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
            .select_related('publisher')\
            .prefetch_related('authors')\
            .order_by('pub_date')
    return render(request, 'template3.html', {'books': books, 'start': start, 'end': end})

def get_books_by_date_with_author_cached(request, start, end):
    """
    books_by_date with all the trimmings, plus caching.  This is potentially dangerous if we know
    the Book queryset we get will be large.
    """
    cache_key = 'booksbydate.{}.{}'.format(start, end)
    books = cache.get(cache_key)
    if not books:
        start = dateutil.parser.parse(start)
        end = dateutil.parser.parse(end)
        books = Book.objects.filter(pub_date__gte=start, pub_date__lte=end)\
                .select_related('publisher')\
                .prefetch_related('authors')\
                .order_by('pub_date')
        cache.set(cache_key, books, 60*60)
    return render(request, 'template3.html', {'books': books, 'start': start, 'end': end})
