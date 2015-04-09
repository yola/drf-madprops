from mock import Mock

from tests import SerializerTestCase, TestPreference, TestUser
from madprops.serializers import PropertiesSerializer


class TestSerializer(PropertiesSerializer):
    class Meta:
        model = TestPreference
        read_only_props = ('user_token',)


class FieldToNative(SerializerTestCase):
    def setUp(self):
        self.preferences = {'k1': 'v1', 'k2': 'v2'}
        user = TestUser()
        user.preferences = self.preferences
        self.representation = TestSerializer().field_to_native(
            user, 'preferences')

    def test_converts_properties_to_dict(self):
        self.assertEqual(self.preferences, self.representation)


class FromNative(SerializerTestCase):
    def setUp(self):
        data = {'k1': 'v1'}
        context = {'view': Mock(kwargs={'user_id': 4})}
        serializer = TestSerializer(context=context)
        self.patch_from_native()
        self.preference = serializer.from_native(data)

    def test_passes_updated_data_to_parent_method(self):
        self.assertEqual(self.preference, TestPreference('k1', 'v1', 4))


class Data(SerializerTestCase):
    def setUp(self):
        serializer = TestSerializer(
            many=True, instance=(
                TestPreference('a', 'b'), TestPreference('c', 'd')))
        self.data = serializer.data

    def test_converts_properties_to_dict(self):
        self.assertEqual(self.data, {'a': 'b', 'c': 'd'})


class ErrorsWhenDataIsNotDict(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(data=[])

    def test_returns_error(self):
        self.assertEqual(
            self.serializer.errors,
            {'non_field_errors': ['Expected a dictionary.']}
        )


class ErrorsForObjectsUpdate(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(
            data={'a': 'b', 'c': 'd'},
            instance=(TestPreference('a', 'aa'),),
            many=True,
            context={'view': Mock(kwargs={'user_id': 4})}
        )
        self.patch_from_native()
        self.serializer.errors

    def test_updates_properties(self):
        self.assertEqual(
            sorted(self.serializer.object),
            sorted([TestPreference('a', 'b'), TestPreference('c', 'd', 4)])
        )


class ErrorsForObjectsCreate(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(
            data={'a': 'b', 'c': 'd'},
            many=True,
            context={'view': Mock(kwargs={'user_id': 4})}
        )
        self.patch_from_native()
        self.serializer.errors

    def test_updates_properties(self):
        self.assertEqual(
            sorted(self.serializer.object),
            sorted([TestPreference('a', 'b', 4), TestPreference('c', 'd', 4)])
        )


class ErrorsForReadOnlyProperties(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(
            data={'a': 'b', 'user_token': 'new_value'},
            many=True,
            context={'view': Mock(kwargs={'user_id': 4})}
        )
        self.patch_from_native()
        self.serializer.errors

    def test_skips_readonly_prpertieso(self):
        self.assertEqual(
            self.serializer.object,
            [TestPreference('a', 'b', 4)]
        )
