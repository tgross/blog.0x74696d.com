from django import db
from django.db import connection
from django.test import TestCase
from django.test.client import RequestFactory

from books.views import *

class BooksTest(TestCase):

    def setUp(self):
        db.reset_queries()

    def test_get_books_by_date(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test shows a single SELECT query.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date(request, '2013-05-16', '2013-05-31')
            print len(connection.queries)
            self.assertEquals(len(connection.queries), 1)

    def test_get_books_by_date_bad(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test shows a 1+n SELECT query.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date_bad(request, '2013-05-16', '2013-05-31')
            print len(connection.queries)
            self.assertEquals(len(connection.queries), 14)

    def test_get_books_by_date_good(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test has been corrected from the above and shows 1 SELECT query.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date_good(request, '2013-05-16', '2013-05-31')
            print len(connection.queries)
            self.assertEquals(len(connection.queries), 1)

    def test_get_books_with_author_bad(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test shows a 1+n many-to-many query.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date_with_author_bad(request, '2013-05-16', '2013-05-31')
            print len(connection.queries)
            self.assertEquals(len(connection.queries), 14)

    def test_get_books_with_author_good(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test has been corrected from the above and shows 2 SELECT queries that are then
        joined in Python.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date_with_author_good(request, '2013-05-16', '2013-05-31')
            print len(connection.queries)
            self.assertEquals(len(connection.queries), 2)

    def test_get_books_with_author_cached(self):
        """
        Given a range of dates strings, return books published between those dates (inclusive).
        This test shows a cached query is will not add to the `connection.queries` list.
        """
        with self.settings(DEBUG=True):
            request = RequestFactory().get('/')
            response = get_books_by_date_with_author_cached(request, '2013-05-16', '2013-05-31')
            db.reset_queries()
            response = get_books_by_date_with_author_cached(request, '2013-05-16', '2013-05-31')
            self.assertEqual(len(connection.queries), 0)

