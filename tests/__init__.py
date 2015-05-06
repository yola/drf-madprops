from django.conf import settings
from mock import Mock, patch
from unittest2 import TestCase

settings.configure()

# Need to import this after configure()
from django.db.models import ForeignKey


class TestPreference(object):

    _meta = Mock(fields=[ForeignKey('user', name='user')])
    objects = Mock()

    def __init__(self, name, value, user=None):
        self.name = name
        self.value = value
        self.user = user

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return '<{name}:{value}:{user}>'.format(**self.__dict__)

    def __cmp__(self, other):
        return cmp(self.name, other.name)


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
            'madprops.serializers.ModelSerializer.to_internal_value',
            new=lambda self, data: TestPreference(
                data['name'], data['value'], data.get('user'))
        )
        self.patched_from_native = patcher.start()
        self.addCleanup(patcher.stop)
