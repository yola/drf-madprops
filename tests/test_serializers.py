from mock import Mock

from tests import SerializerTestCase, TestPreference, TestUser
from madprops.serializers import PropertiesSerializer


class TestSerializer(PropertiesSerializer):
    class Meta:
        model = TestPreference
        parent_obj_name = 'user'


class FieldToRepresentation(SerializerTestCase):
    def setUp(self):
        self.preferences = {'k1': 'v1', 'k2': 'v2'}
        user = TestUser()
        user.preferences = self.preferences
        self.representation = TestSerializer().field_to_native(
            user, 'preferences')

    def test_converts_properties_to_dict(self):
        self.assertEqual(self.preferences, self.representation)


class PropertyToInternalValue(SerializerTestCase):
    def setUp(self):
        data = {'k1': 'v1'}
        context = {'view': Mock(kwargs={'user_id': 4})}
        serializer = TestSerializer(context=context)
        self.patch_from_native()
        self.preference = serializer.from_native(data)

    def test_passes_updated_data_to_parent_method(self):
        self.assertEqual(self.preference, TestPreference('k1', 'v1', 4))


class DataForSingleObject(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(instance=TestPreference('a', 'b'))

    def test_converts_property_to_dict(self):
        self.assertEqual(self.serializer.data, {'value': 'b'})


class DataForMultipleObjects(SerializerTestCase):
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


class ErrorsForMultipleObjectsUpdate(SerializerTestCase):
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


class ErrorsForSingleObjectUpdate(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(
            data={'value': 'aaa'},
            instance=TestPreference('a', 'b'),
        )
        self.serializer.errors

    def test_updates_properties(self):
        self.assertEqual(self.serializer.object, TestPreference('a', 'aaa'))


class ErrorsForSingleObjectCreate(SerializerTestCase):
    def setUp(self):
        self.serializer = TestSerializer(
            data={'a': 'b'},
            context={'view': Mock(kwargs={'user_id': 4})}
        )
        self.patch_from_native()
        self.serializer.errors

    def test_updates_properties(self):
        self.assertEqual(self.serializer.object, TestPreference('a', 'b', 4))


class ErrorsForMultipleObjectsCreate(SerializerTestCase):
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
