from django.conf import settings
from mock import Mock, patch
from unittest2 import TestCase

settings.configure(
    DEFAULT_INDEX_TABLESPACE='',
)


class TestPreference(object):
    def __init__(self, name, value, user=None):
        self.name = name
        self.value = value
        self.user = user

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return '<{name}:{value}:{user}>'.format(**self.__dict__)


class TestUser(object):

    @property
    def preferences(self):
        return Mock(all=Mock(return_value=self._preferences))

    @preferences.setter
    def preferences(self, value):
        self._preferences = [
            TestPreference(k, v) for k, v in value.iteritems()]


class SerializerTestCase(TestCase):

    def patch_from_native(self):
        patcher = patch(
            'madprops.serializers.ModelSerializer.from_native',
            new=lambda self, data, files: TestPreference(
                data['name'], data['value'], data.get('user'))
        )
        self.patched_from_native = patcher.start()
        self.addCleanup(patcher.stop)
