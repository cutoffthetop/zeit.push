from zeit.cms.testcontenttype.testcontenttype import ExampleContentType
from zeit.cms.workflow.interfaces import IPublish, IPublishInfo
import zeit.push.interfaces
import zeit.push.testing
import zeit.workflow.testing
import zope.component


class MessageTest(zeit.push.testing.TestCase):

    def create_content(self, short_text=None):
        content = ExampleContentType()
        if short_text is not None:
            push = zeit.push.interfaces.IPushMessages(content)
            push.short_text = 'mytext'
        self.repository['foo'] = content
        return self.repository['foo']

    def test_send_delegates_to_IPushNotifier_utility(self):
        content = self.create_content('mytext')
        message = zope.component.getAdapter(
            content, zeit.push.interfaces.IMessage, name='twitter')
        message.send()
        twitter = zope.component.getUtility(
            zeit.push.interfaces.IPushNotifier, name='twitter')
        self.assertEqual(
            [('mytext', u'http://www.zeit.de/foo', {})], twitter.calls)

    def test_no_text_configured_should_not_send(self):
        content = self.repository['testcontent']
        message = zope.component.getAdapter(
            content, zeit.push.interfaces.IMessage, name='twitter')
        with self.assertRaises(ValueError):
            message.send()
        twitter = zope.component.getUtility(
            zeit.push.interfaces.IPushNotifier, name='twitter')
        self.assertEqual([], twitter.calls)

    def publish(self, content):
        IPublishInfo(content).urgent = True
        IPublish(content).publish()
        zeit.workflow.testing.run_publish()

    def test_enabled_flag_is_removed_from_service_after_send(self):
        content = self.create_content('mytext')
        push = zeit.push.interfaces.IPushMessages(content)
        push.message_config = [{'type': 'twitter', 'enabled': True}]
        self.publish(content)
        self.assertEqual(
            [{'type': 'twitter', 'enabled': False}], push.message_config)
