from zeit.cms.i18n import MessageFactory as _
import xml.sax.saxutils
import zc.sourcefactory.source
import zeit.cms.content.sources
import zope.interface
import zope.schema


class IMessage(zope.interface.Interface):

    get_text_from = zope.interface.Attribute(
        'Fieldname from `IPushMessages` to read the text for the notification')

    text = zope.interface.Attribute(
        'Property that can be overriden if `get_text_from` is not sufficient '
        'to retrieve the text for the notification')

    additional_parameters = zope.interface.Attribute(
        'Additional parameters that should be send to `IPushNotifier` as **kw')

    def send():
        """Send push notification to external service via `IPushNotifier`.

        Will fetch the `IPushNotifier` utility using the name that was used to
        register this `IMessage` adapter. Calls the utility providing the
        message config, `additional_parameters`, `text` and a link to context
        as parameters.

        Currently `additional_parameters` is only used for mobile push
        notifications to enrich the parameteres with `teaserTitle`,
        `teaserText`, `teaserSupertitle` and `image_url`. These information are
        read from the context.

        """


class IPushNotifier(zope.interface.Interface):

    def send(text, link, **kw):
        """Sends given ``text`` as a push message through an external service.

        The ``link`` (an URL) will be integrated into the message (how this
        happens depends on the medium, possibilities include appending to the
        text, attaching as metadata, etc.).

        Additional kw parameters:

        * ``type``: Name of the external service.

        * ``enabled``: If the service is enabled.

        * ``channels``: Restrict push notification to users listening to this
          kind of pushes (`News` or `Eilmeldung`). [only `mobile`]

        * ``override_text``: Text that should be used instead of the given
          `text` parameter. [only `mobile` & `facebook`]

        * ``account``: Send push notification using given account.
          [only `facebook` & `twitter`]

        """


class WebServiceError(Exception):
    """Web service was unable to process a request due to semantic problems.

    For example, a response with HTTP status code "401 Unauthorized" should
    raise this error.

    """


class TechnicalError(Exception):
    """Web service was unable to process a request due to technical errors.

    For example, a response with HTTP status code "500 Server Error" should
    raise this error.

    """


class IPushMessages(zope.interface.Interface):
    """Configures push services that are notified if context is published.

    Available services are stored in `message_config` on checkin of context.
    When the context is published, send a push notification for each stored
    service whose configuration defines it as `enabled` by looking up a named
    `IMessage` adapter that forwards the actual push to an `IPushNotifier`
    utility.

    """

    date_last_pushed = zope.schema.Datetime(
        title=_('Last push'), required=False, readonly=True)

    # BBB deprecated, Facebook texts are now stored per account in
    # message_config.
    long_text = zope.schema.Text(
        title=_('Long push text'), required=False)
    short_text = zope.schema.TextLine(
        title=_('Short push text'),
        required=False,
        # 117 + 1 Space + 23 characters t.co-URL = 140
        #
        # XXX It's not yet clear what we can do when the user enters another
        # URL as part of the tweet and that URL gets *longer* during the
        # shortening process.
        max_length=116)

    """A message configuration is a dict with at least the following keys:
       - type: Kind of service (twitter, facebook, ...). Must correspond
         to the utility name of an IPushNotifier.
       - enabled: Boolean. This allows keeping the message configuration even
         when it should not be used at the moment, e.g. for different text to
         different accounts.

    Any other keys are type-dependent. (A common additional key is ``account``,
    e.g. Twitter and Facebook support posting to different accounts.)

    """
    message_config = zope.schema.Tuple(required=False, default=())

    messages = zope.interface.Attribute(
        'List of IMessage objects, one for each enabled message_config entry')


CONFIG_CHANNEL_NEWS = 'channel-news'
CONFIG_CHANNEL_BREAKING = 'channel-breaking'


class IPushURL(zope.interface.Interface):
    """Interface to adapt `ICMSContent` to the base URL for push notifications.

    Usually the result is the `uniqueId` of the `ICMSContent`, but this
    interface serves as an extension point for special treatments of certain
    content types, e.g. `zeit.content.link` objects.

    """


class TwitterAccountSource(zeit.cms.content.sources.XMLSource):

    product_configuration = 'zeit.push'
    config_url = 'twitter-accounts'
    attribute = 'name'

    class source_class(zc.sourcefactory.source.FactoredContextualSource):

        @property
        def MAIN_ACCOUNT(self):
            return self.factory.main_account()

    @classmethod
    def main_account(cls):
        config = zope.app.appsetup.product.getProductConfiguration(
            cls.product_configuration)
        return config['twitter-main-account']

    def isAvailable(self, node, context):
        return (
            super(TwitterAccountSource, self).isAvailable(node, context) and
            node.get('name') != self.main_account())

    def access_token(self, value):
        tree = self._get_tree()
        nodes = tree.xpath('%s[@%s= %s]' % (
                           self.title_xpath,
                           self.attribute,
                           xml.sax.saxutils.quoteattr(value)))
        if not nodes:
            return (None, None)
        node = nodes[0]
        return (node.get('token'), node.get('secret'))

twitterAccountSource = TwitterAccountSource()


class FacebookAccountSource(zeit.cms.content.sources.XMLSource):

    product_configuration = 'zeit.push'
    config_url = 'facebook-accounts'
    attribute = 'name'

    class source_class(zc.sourcefactory.source.FactoredContextualSource):

        @property
        def MAIN_ACCOUNT(self):
            return self.factory.main_account()

        @property
        def MAGAZIN_ACCOUNT(self):
            return self.factory.magazin_account()

        @property
        def CAMPUS_ACCOUNT(self):
            return self.factory.campus_account()

    @classmethod
    def main_account(cls):
        config = zope.app.appsetup.product.getProductConfiguration(
            cls.product_configuration)
        return config['facebook-main-account']

    @classmethod
    def magazin_account(cls):
        config = zope.app.appsetup.product.getProductConfiguration(
            cls.product_configuration)
        return config['facebook-magazin-account']

    @classmethod
    def campus_account(cls):
        config = zope.app.appsetup.product.getProductConfiguration(
            cls.product_configuration)
        return config['facebook-campus-account']

    def isAvailable(self, node, context):
        return (
            super(FacebookAccountSource, self).isAvailable(node, context) and
            node.get('name') != self.main_account())

    def access_token(self, value):
        tree = self._get_tree()
        nodes = tree.xpath('%s[@%s= %s]' % (
                           self.title_xpath,
                           self.attribute,
                           xml.sax.saxutils.quoteattr(value)))
        if not nodes:
            return (None, None)
        node = nodes[0]
        return node.get('token')

facebookAccountSource = FacebookAccountSource()


class IAccountData(zope.interface.Interface):
    """Convenience access to IPushMessages.message_config entries"""

    facebook_main_enabled = zope.schema.Bool(title=_('Enable Facebook'))
    facebook_main_text = zope.schema.Text(
        title=_('Facebook Main Text'), required=False)

    facebook_magazin_enabled = zope.schema.Bool(
        title=_('Enable Facebook Magazin'))
    facebook_magazin_text = zope.schema.Text(
        title=_('Facebook Magazin Text'), required=False)

    facebook_campus_enabled = zope.schema.Bool(
        title=_('Enable Facebook Campus'))
    facebook_campus_text = zope.schema.Text(
        title=_('Facebook Campus Text'), required=False)

    twitter_main_enabled = zope.schema.Bool(title=_('Enable Twitter'))
    twitter_ressort_enabled = zope.schema.Bool(
        title=_('Enable Twitter Ressort'))
    twitter_ressort = zope.schema.Choice(
        title=_('Additional Twitter'),
        source=twitterAccountSource,
        required=False)

    mobile_text = zope.schema.TextLine(title=_('Mobile title'), required=False)
    mobile_enabled = zope.schema.Bool(title=_('Enable mobile push'))
