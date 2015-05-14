import json

from mock import call, Mock, patch

from tests import SerializerTestCase, TestPreference, TestUser
from madprops.serializers import PropertySerializer, PropertiesOwnerSerializer
from rest_framework.serializers import ValidationError
import rest_framework
from unittest2 import TestCase


from django.db import models

# Fake models and serializers for them. We have separate models for
# serialize and de-serialize operations, because we don't need foreign key
# for serialize testcases, and don't want to have needless mocks.
class User(models.Model):
    name = models.CharField(null=False, max_length=150)


class UserPreference(models.Model):
    name = models.CharField(null=False, max_length=150)
    value = models.CharField(null=False, max_length=150)


class PreferenceSerializer(PropertySerializer):
    class Meta:
        model = UserPreference
        json_props = ('json_prop',)
        read_only_props = ()


class UserSerializer(PropertiesOwnerSerializer):
    class Meta:
        model = User

    preferences = PreferenceSerializer(many=True, required=False)


# The following models are used to test JSON -> Object conversions tests.
class UserForWrite(models.Model):
    name = models.CharField(null=False, max_length=150)


class PreferenceForWrite(models.Model):
    user = models.ForeignKey(User, related_name='preferences')
    name = models.CharField(null=False, max_length=150)
    value = models.CharField(null=False, max_length=150)


class PreferenceSerializerForWrite(PropertySerializer):
    class Meta:
        model = PreferenceForWrite
        json_props = ('json_prop',)
        read_only_props = ()


class UserSerializerForWrite(PropertiesOwnerSerializer):
    class Meta:
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
        self.json_value = json.dumps({1:1})

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


class DeserializeSingleProperty(TestCase):
    @patch('rest_framework.relations.RelatedField.get_queryset')
    @patch.object(PreferenceForWrite, 'objects')
    @patch.object(PreferenceForWrite, 'save')
    def setUp(self, save_mock, manager_mock, get_queryset_mock):
        # This emulates property in the database, which needs to be updated
        # as a result of given test.
        self.existing_prop_mock = Mock(name='name', value='value')

        filter_mock = Mock()
        filter_mock.first = Mock(return_value=self.existing_prop_mock)
        manager_mock.filter = Mock(return_value=filter_mock)

        get_queryset_mock.return_value=Mock(get=Mock(return_value=1))

        self.json_value_new = {1: None}

        self.serializer = PreferenceSerializerForWrite(
            data={'json_prop': self.json_value_new}, context={
                'view': Mock(kwargs={'user_id': 1})})
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(dict(self.serializer.validated_data),
            {'name': 'json_prop',
             'value': json.dumps(self.json_value_new),
             'user': 1})

    def test_save_called_on_correct_object(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, json.dumps(self.json_value_new))


class DeserializeMultipleProperties(TestCase):
    @patch('rest_framework.relations.RelatedField.get_queryset')
    @patch.object(PreferenceForWrite, 'objects')
    @patch.object(PreferenceForWrite, 'save')
    def setUp(self, save_mock, manager_mock, get_queryset_mock):
        self.manager_mock = manager_mock

        filter_mock = Mock()
        self.existing_prop_mock = Mock(name='prop1', value='value1')
        filter_mock.first.side_effect = [self.existing_prop_mock, None]
        manager_mock.filter = Mock(return_value=filter_mock)
        get_queryset_mock.return_value=Mock(get=Mock(return_value=1))

        self.serializer = PreferenceSerializerForWrite(
            data={'prop1': 'value_new', 'prop2': 'value2'}, context={
                'view': Mock(kwargs={'user_id': 1})}, many=True)
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data,
            [{'name': 'prop1', 'value': 'value_new', 'user': 1},
             {'name': 'prop2', 'value': 'value2', 'user': 1}])

    def test_existing_property_is_updated(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, 'value_new')

    def test_new_property_is_created(self):
        self.manager_mock.create.assert_called_once_with(
            name='prop2', value='value2', user=1)


class DeserializePropertiesOwner(TestCase):
    @patch('rest_framework.relations.RelatedField.get_queryset')
    @patch.object(PreferenceForWrite, 'objects')
    @patch.object(PreferenceForWrite, 'save')
    @patch.object(User, 'save')
    def setUp(self, user_save_mock, save_mock, manager_mock, get_queryset_mock):
        self.manager_mock = manager_mock
        self.user_save_mock = user_save_mock
        filter_mock = Mock()
        self.existing_prop_mock = Mock(name='prop1', value='value1')
        filter_mock.first.side_effect = [self.existing_prop_mock, None]
        manager_mock.filter = Mock(return_value=filter_mock)
        get_queryset_mock.return_value=Mock(get=Mock(return_value=1))

        user = User(name='username', id=1)

        self.serializer = UserSerializerForWrite(user,
            data={'name': 'new_username', 'preferences': {
                'prop1': 'value_new',
                'prop2': 'value2'}}, context={
                'view': Mock(kwargs={'user_id': 1})})
        self.serializer.is_valid()

        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, {
            'name': 'new_username', 'preferences':
            [{'name': 'prop1', 'value': 'value_new', 'user': 1},
             {'name': 'prop2', 'value': 'value2', 'user': 1}]})

    def test_existing_property_is_updated(self):
        self.assertEqual(self.existing_prop_mock.save.call_count, 1)
        self.assertEqual(
            self.existing_prop_mock.value, 'value_new')

    def test_new_property_is_created(self):
        self.manager_mock.create.assert_called_once_with(
            name='prop2', value='value2', user=1)

    def test_owner_is_updated(self):
        self.assertEqual(self.user_save_mock.call_count, 1)
