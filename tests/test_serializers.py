import json
import operator
from unittest import TestCase

from django.db import connection, models
from django.test import TestCase as DjangoTestCase
from madprops.serializers import PropertiesOwnerSerializer, PropertySerializer
from rest_framework.exceptions import ValidationError

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class User(models.Model):
    name = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


class Preference(models.Model):
    user = models.ForeignKey(
        User, related_name='preferences', on_delete=models.CASCADE)
    name = models.CharField(null=False, max_length=150)
    value = models.CharField(null=False, max_length=150)

    class Meta:
        app_label = 'testapp'


with connection.schema_editor() as schema_editor:
    for model in [User, Preference]:
        schema_editor.create_model(model)


class PreferenceSerializer(PropertySerializer):
    class Meta:
        model = Preference
        json_props = ('json_prop',)
        read_only_props = ()
        fields = ('user', 'name', 'value')


class UserSerializer(PropertiesOwnerSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'preferences')

    preferences = PreferenceSerializer(many=True, required=False)


class SerializeSingleProperty(TestCase):
    def setUp(self):
        obj = Preference(name='name1', value='value1')
        self.serializer = PreferenceSerializer(obj)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {'name1': 'value1'})


class SerializeMultipleProperties(TestCase):
    def setUp(self):
        prefs = [Preference(name='name1', value='value1'),
                 Preference(name='name2', value='value2')]
        self.serializer = PreferenceSerializer(prefs, many=True)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {
            'name1': 'value1', 'name2': 'value2'})


class SerializeJsonProperty(TestCase):
    def setUp(self):
        self.json_value = json.dumps({1: 1})

        prefs = [Preference(name='name1', value='value1'),
                 Preference(name='json_prop', value=self.json_value)]
        self.serializer = PreferenceSerializer(prefs, many=True)

    def test_property_serialized_correctly(self):
        self.assertEqual(self.serializer.data, {
            'name1': 'value1', 'json_prop': json.loads(self.json_value)})


class SerializePropertiesOwner(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create(name='username')
        Preference.objects.create(
            user=self.user, name='name1', value='value1')
        Preference.objects.create(
            user=self.user, name='name2', value='value2')
        self.serializer = UserSerializer(self.user)

    def test_property_serialized_correctly(self):
        expected_result = {
            'id': self.user.id,
            'name': 'username',
            'preferences': {'name1': 'value1', 'name2': 'value2'}}
        self.assertEqual(self.serializer.data, expected_result)


class DeserializeSingleProperty(DjangoTestCase):

    def setUp(self):
        self.user = User.objects.create(name='username')
        self.existing_prop = Preference.objects.create(
            user=self.user, name='name', value='value')

        self.json_value_new = {1: None}
        self.serializer = PreferenceSerializer(
            data={'json_prop': self.json_value_new},
            context={'view': Mock(kwargs={'user_id': self.user.id})}
        )
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, {
            'name': 'json_prop',
            'value': json.dumps(self.json_value_new),
            'user': self.user
        })

    def test_new_property_is_created(self):
        new_prop = Preference.objects.get(
            user=self.user,
            name='json_prop',
            value=json.dumps(self.json_value_new)
        )
        self.assertNotEqual(new_prop.id, self.existing_prop.id)


class DeserializeMultipleProperties(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create(name='username')
        self.existing_prop = Preference.objects.create(
            user=self.user, name='prop1', value='value1')
        self.serializer = PreferenceSerializer(
            data={'prop1': 'value_new', 'prop2': 'value2'},
            context={'view': Mock(kwargs={'user_id': self.user.id})},
            many=True)
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        actual_data = sorted(
            self.serializer.validated_data, key=operator.itemgetter('name'))
        self.assertEqual(actual_data, [
            {'name': 'prop1', 'value': 'value_new', 'user': self.user},
            {'name': 'prop2', 'value': 'value2', 'user': self.user},
        ])

    def test_existing_property_is_updated(self):
        self.existing_prop.refresh_from_db()
        self.assertEqual(self.existing_prop.name, 'prop1')
        self.assertEqual(self.existing_prop.value, 'value_new')

    def test_new_property_is_created(self):
        self.assertTrue(Preference.objects.filter(
            user=self.user, name='prop2', value='value2'
        ).exists())


class DeserializePropertiesOwner(DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create(name='username')
        self.existing_prop = Preference.objects.create(
            user=self.user, name='prop1', value='value1')

        self.serializer = UserSerializer(self.user, data={
            'name': 'new_username',
            'preferences': {
                'prop1': 'value_new',
                'prop2': 'value2'
            }},
            context={'view': Mock(kwargs={'user_id': self.user.id})})
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        actual_data = self.serializer.validated_data.copy()
        actual_data['preferences'] = sorted(
            actual_data['preferences'], key=operator.itemgetter('name'))
        self.assertEqual(actual_data, {
            'name': 'new_username',
            'preferences': [
                {'name': 'prop1', 'value': 'value_new', 'user': self.user},
                {'name': 'prop2', 'value': 'value2', 'user': self.user}
            ]
        })

    def test_existing_property_is_updated(self):
        self.existing_prop.refresh_from_db()
        self.assertEqual(self.existing_prop.name, 'prop1')
        self.assertEqual(self.existing_prop.value, 'value_new')

    def test_new_property_is_created(self):
        self.assertTrue(Preference.objects.filter(
            user=self.user, name='prop2', value='value2'
        ).exists())

    def test_owner_is_updated(self):
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'new_username')


class DeserializePropertiesOwnerWhenOptionalPropertiesOmitted(
        DjangoTestCase):
    def setUp(self):
        self.user = User.objects.create(name='username')

        self.serializer = UserSerializer(
            self.user,
            data={'name': 'new_username'},
            context={'view': Mock(kwargs={'user_id': self.user.id})})
        self.serializer.is_valid()
        self.serializer.save()

    def test_data_is_validated_correctly(self):
        self.assertEqual(self.serializer.validated_data, {
            'name': 'new_username'})

    def test_no_new_properties_are_created(self):
        self.assertFalse(Preference.objects.exists())


class DeserializePropertiesForNonDictData(TestCase):
    def setUp(self):
        self.serializer = PreferenceSerializer(
            data=['one', 'two', 'three'])

    def test_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.serializer.is_valid(raise_exception=True)
