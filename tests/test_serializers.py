import json

from django.db import models
from mock import Mock, patch

from madprops.serializers import PropertiesOwnerSerializer, PropertySerializer
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError
from unittest2 import TestCase


# Fake models and serializers for them. We have separate models for
# serialize and de-serialize operations, because we don't need foreign key
# for serialize testcases, and don't want to have needless mocks.
class User(models.Model):
    name = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


class UserPreference(models.Model):
    name = models.CharField(null=False, max_length=150)
    value = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


class PreferenceSerializer(PropertySerializer):
    class Meta:
        model = UserPreference
        json_props = ('json_prop',)
        read_only_props = ()


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

    preferences = PreferenceSerializer(many=True, required=False)


# The following models are used to test JSON -> Object conversions tests.
class UserForWrite(models.Model):
    name = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


class PreferenceForWrite(models.Model):
    user = models.ForeignKey(User, related_name='preferences')
    name = models.CharField(null=False, max_length=150)
    value = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


class PreferenceSerializerForWrite(PropertySerializer):
    class Meta:
        fields = '__all__'
        model = PreferenceForWrite
        json_props = ('json_prop',)
        read_only_props = ()


class UserSerializerForWrite(PropertiesOwnerSerializer):
    class Meta:
        fields = '__all__'
        model = UserForWrite

    preferences = PreferenceSerializerForWrite(many=True, required=False)


class SerializeSingleProperty(TestCase):
    def setUp(self):
        obj = UserPreference(name='name1', value='value1')
        self.serializer = PreferenceSerializer(obj)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {'name1': 'value1'})


class SerializeMultipleProperties(TestCase):
    def setUp(self):
        prefs = [UserPreference(name='name1', value='value1'),
                 UserPreference(name='name2', value='value2')]
        self.serializer = PreferenceSerializer(prefs, many=True)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {
            'name1': 'value1', 'name2': 'value2'})


class SerializeJsonProperty(TestCase):
    def setUp(self):
        self.json_value = json.dumps({1: 1})

        prefs = [UserPreference(name='name1', value='value1'),
                 UserPreference(name='json_prop', value=self.json_value)]
        self.serializer = PreferenceSerializer(prefs, many=True)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {
            'name1': 'value1', 'json_prop': json.loads(self.json_value)})


class SerializePropertiesOwner(TestCase):
    def setUp(self):
        prefs = [UserPreference(name='name1', value='value1'),
                 UserPreference(name='name2', value='value2')]
        user = UserForWrite(name='username')
        user.preferences = prefs
        self.serializer = UserSerializer(user)

    def test_property_serialized_correctly(self):
        expected_result = {
            'id': None, 'name': 'username',
            'preferences': {'name1': 'value1', 'name2': 'value2'}}
        self.assertEqual(self.serializer.data, expected_result)


class MockDBMixin(object):
    def _mock_db(self):
        self.get_queryset_mock = patch(
            'rest_framework.relations.RelatedField.get_queryset').start()
        self.manager_mock = patch.object(PreferenceForWrite, 'objects').start()
        self.save_mock = patch.object(PreferenceForWrite, 'save').start()
        self.user_save_mock = patch.object(User, 'save').start()

        self.manager_mock.filter = self.existing_props_mock
        self.get_queryset_mock.return_value = Mock(get=Mock(return_value=1))
        self.get_queryset_mock.__func__ = self.get_queryset_mock

        self.addCleanup(self.manager_mock.stop)
        self.addCleanup(self.save_mock.stop)
        self.addCleanup(self.user_save_mock.stop)
        self.addCleanup(self.get_queryset_mock)

    @property
    def existing_props_mock(self):
        return []


class DeserializeSingleProperty(TestCase, MockDBMixin):
    @property
    def existing_props_mock(self):
        self.existing_prop_mock = Mock(name='name', value='value')
        return Mock(return_value=[self.existing_prop_mock])

    def setUp(self):
        # This emulates property in the database, which needs to be updated
        # as a result of given test.
        self._mock_db()

        self.json_value_new = {1: None}
        self.serializer = PreferenceSerializerForWrite(
            data={'json_prop': self.json_value_new}, context={
                'view': Mock(kwargs={'user_id': 1})})
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(
            dict(self.serializer.validated_data), {
                'name': 'json_prop',
                'value': json.dumps(self.json_value_new),
                'user': 1})

    def test_save_called_on_correct_object(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, json.dumps(self.json_value_new))


class DeserializeMultipleProperties(TestCase, MockDBMixin):
    def setUp(self):
        self._mock_db()

        self.serializer = PreferenceSerializerForWrite(
            data={'prop1': 'value_new', 'prop2': 'value2'}, context={
                'view': Mock(kwargs={'user_id': 1})}, many=True)
        self.serializer.is_valid()
        self.serializer.save()

    @property
    def existing_props_mock(self):
        self.existing_prop_mock = Mock(name='prop1', value='value1')
        return Mock(side_effect=[[self.existing_prop_mock], []])

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, [
            {'name': 'prop1', 'value': 'value_new', 'user': 1},
            {'name': 'prop2', 'value': 'value2', 'user': 1}])

    def test_existing_property_is_updated(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, 'value_new')

    def test_new_property_is_created(self):
        self.manager_mock.create.assert_called_once_with(
            name='prop2', value='value2', user=1)


class DeserializePropertiesOwner(TestCase, MockDBMixin):
    def setUp(self):
        self._mock_db()
        self.user = User(name='username', id=1)

        self.serializer = UserSerializerForWrite(self.user, data={
            'name': 'new_username', 'preferences': {
                'prop1': 'value_new',
                'prop2': 'value2'}},
            context={'view': Mock(kwargs={'user_id': 1})})
        self.serializer.is_valid()
        self.serializer.save()

    @property
    def existing_props_mock(self):
        self.existing_prop_mock = Mock(name='prop1', value='value1')
        return Mock(side_effect=[[self.existing_prop_mock], []])

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, {
            'name': 'new_username', 'preferences':
            [{'name': 'prop1', 'value': 'value_new', 'user': self.user},
             {'name': 'prop2', 'value': 'value2', 'user': self.user}]})

    def test_existing_property_is_updated(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, 'value_new')

    def test_new_property_is_created(self):
        self.manager_mock.create.assert_called_once_with(
            name='prop2', value='value2', user=self.user)

    def test_owner_is_updated(self):
        self.assertEqual(self.user_save_mock.call_count, 1)


class DeserializePropertiesOwnerWhenOptionalPropertiesOmitted(
        TestCase, MockDBMixin):
    def setUp(self):
        self._mock_db()
        self.user = User(name='username', id=1)

        self.serializer = UserSerializerForWrite(self.user, data={
            'name': 'new_username'},
            context={'view': Mock(kwargs={'user_id': 1})})
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, {
            'name': 'new_username'})

    def test_no_new_properties_are_created(self):
        self.assertFalse(self.manager_mock.create.called)


class DeserializePropertiesForNonDictData(TestCase):
    def setUp(self):
        self.serializer = PreferenceSerializerForWrite(
            data=['one', 'two', 'three'])

    def test_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.serializer.is_valid(raise_exception=True)
