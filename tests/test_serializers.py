import json

from mock import Mock

from tests import SerializerTestCase, TestPreference, TestUser
from madprops.serializers import PropertySerializer


class TestSerializer(PropertySerializer):
    class Meta:
        model = TestPreference
        read_only_props = ('user_token',)
        json_props = ('json1', )


class FieldToNative(SerializerTestCase):
    def setUp(self):
        self.preferences = {'k1': 'v1', 'k2': 'v2'}
        user = TestUser()
        user.preferences = self.preferences
        self.representation = TestSerializer().field_to_native(
            user, 'preferences')

    def test_converts_properties_to_dict(self):
        self.assertEqual(self.preferences, self.representation)


class FieldToNativeWhenObjectIsNone(SerializerTestCase):
    def setUp(self):
        self.representation = TestSerializer().field_to_native(
            None, 'preferences')

    def test_returns_None(self):
        self.assertIsNone(self.representation)


class FromNative(SerializerTestCase):
    def setUp(self):
        data = {'k1': 'v1'}
        context = {'view': Mock(kwargs={'user_id': 4})}
        serializer = TestSerializer(context=context)
        self.patch_from_native()
        self.preference = serializer.from_native(data)

    def test_passes_updated_data_to_parent_method(self):
        self.assertEqual(self.preference, TestPreference('k1', 'v1', 4))


class FromNativeForJsonProperty(SerializerTestCase):
    def setUp(self):
        data = {'json1': [1, 2]}
        context = {'view': Mock(kwargs={'user_id': 4})}
        serializer = TestSerializer(context=context)
        self.patch_from_native()
        self.preference = serializer.from_native(data)

    def test_converts_value_to_json(self):
        self.assertEqual(
            self.preference, TestPreference('json1', json.dumps([1, 2]), 4))


class Data(SerializerTestCase):
    def setUp(self):
        serializer = TestSerializer(
            many=True, instance=(
                TestPreference('a', 'b'), TestPreference('c', 'd')))
        self.data = serializer.data

    def test_converts_properties_to_dict(self):
        self.assertEqual(self.data, {'a': 'b', 'c': 'd'})


class DataForJsonValues(SerializerTestCase):
    def setUp(self):
        serializer = TestSerializer(
            many=True, instance=(
                TestPreference('json1', json.dumps([1, 3])),
                TestPreference('c', 'd'))
        )
        self.data = serializer.data

    def test_loads_json_properties(self):
        self.assertEqual(self.data, {'json1': [1, 3], 'c': 'd'})


class DataWhenObjectIsNone(SerializerTestCase):
    def setUp(self):
        serializer = TestSerializer(many=True)
        self.data = serializer.data

    def test_returns_None(self):
        self.assertIsNone(self.data)


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
            sorted([TestPreference('a', 'b'), TestPreference('c', 'd', 4)],)
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


class SaveObject(SerializerTestCase):
    def setUp(self):
        self.pref = TestPreference('a', 'b', 'user')
        TestSerializer().save_object(self.pref)
        self.addCleanup(TestPreference.objects.reset_mock)

    def test_tries_to_update_existent_property(self):
        TestPreference.objects.filter.assert_called_once_with(
            user='user', name='a')
        TestPreference.objects.filter().update.assert_called_once_with(
            value='b')
