from datetime import datetime
from zeit.push.testing import parse_settings as settings
import mock
import pytz
import unittest
import zeit.push.parse
import zeit.push.testing
import zope.app.appsetup.product


class ParseTest(unittest.TestCase):

    level = 2

    @unittest.skip('Cannot push to ios without a apple certificate')
    def test_push_works(self):
        # Parse offers no REST API to retrieve push messages,
        # so this is just a smoke test.
        api = zeit.push.parse.Connection(
            settings['application_id'], settings['rest_api_key'], 1)
        api.send('Being pushy.', 'http://example.com')

    def test_invalid_credentials_should_raise(self):
        api = zeit.push.parse.Connection('invalid', 'invalid', 1)
        with self.assertRaises(zeit.push.interfaces.WebServiceError):
            api.send('Being pushy.', 'http://example.com')


class URLRewriteTest(unittest.TestCase):

    def rewrite(self, url):
        return zeit.push.parse.Connection.rewrite_url(url)

    def test_www_zeit_de_is_replaced_with_wrapper(self):
        self.assertEqual(
            'http://wrapper.zeit.de/foo/bar',
            self.rewrite('http://www.zeit.de/foo/bar'))

    def test_blog_zeit_de_is_replaced_with_wrapper_and_appends_query(self):
        self.assertEqual(
            'http://wrapper.zeit.de/blog/foo/bar?feed=articlexml',
            self.rewrite('http://blog.zeit.de/foo/bar'))

    def test_zeit_de_blog_is_replaced_with_wrapper_and_appends_query(self):
        self.assertEqual(
            'http://wrapper.zeit.de/blog/foo/bar?feed=articlexml',
            self.rewrite('http://www.zeit.de/blog/foo/bar'))


class ParametersTest(zeit.push.testing.TestCase):

    def test_sets_expiration_time(self):
        api = zeit.push.parse.Connection(
            'any', 'any', 3600)
        with mock.patch('zeit.push.parse.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(
                2014, 07, 1, 10, 15, 7, 38, tzinfo=pytz.UTC)
            with mock.patch.object(api, 'push') as push:
                api.send('foo', 'any')
                data = push.call_args[0][0]
                self.assertEqual(
                    '2014-07-01T11:15:07+00:00', data['expiration_time'])

    def test_no_channels_given_omits_channels_parameter(self):
        api = zeit.push.parse.Connection(
            'any', 'any', 1)
        with mock.patch.object(api, 'push') as push:
            api.send('foo', 'any')
            data = push.call_args[0][0]
            self.assertNotIn('channels', data)

    def test_channels_string_is_looked_up_in_product_config(self):
        product_config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.push')
        product_config['foo'] = 'bar qux'
        api = zeit.push.parse.Connection(
            'any', 'any', 1)
        with mock.patch.object(api, 'push') as push:
            api.send('foo', 'any', channels='foo')
            data = push.call_args[0][0]
            self.assertEqual(['bar', 'qux'], data['channels'])

    def test_aa_empty_product_config_omits_channels_parameter(self):
        product_config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.push')
        product_config['foo'] = ''
        api = zeit.push.parse.Connection(
            'any', 'any', 1)
        with mock.patch.object(api, 'push') as push:
            api.send('foo', 'any', channels='foo')
            data = push.call_args[0][0]
            self.assertNotIn('channels', data)
