from collections import Iterable
import json

from django.db.models import ForeignKey
from django.utils.functional import cached_property
from rest_framework.serializers import ModelSerializer, ListSerializer


class PropertySerializerOptions(object):
    """Meta class options for PropertySerializer"""
    def __init__(self, meta):
        self.model = getattr(meta, 'model', None)
        self.read_only_props = getattr(meta, 'read_only_props', [])
        self.json_props = getattr(meta, 'json_props', [])
        self.exclude = ('id',)

    @cached_property
    def parent_obj_field(self):
        # Automagically get the name of field containing relation to parent
        for field in self.model._meta.fields:
            if isinstance(field, ForeignKey):
                return field.name

        raise ValueError(
            '{0} misses relation to parent model'.format(self.model))


class NestedPropertySerializerOptions(PropertySerializerOptions):
    """Meta class options for NestedPropertySerializer"""
    def __init__(self, meta):
        super(NestedPropertySerializerOptions, self).__init__(meta)
        self.exclude = ('id', self.parent_obj_field)


class ListToDictSerializer(ListSerializer):
    def to_representation(self, value):
        return super(self, ListToDictSerializer).to_representation(value)

    def to_internal_value(self, data):
        return super(self, ListToDictSerializer).to_representation(data)



class PropertySerializer(ModelSerializer):
    """Allows to operate on properties of certain resource as dictionary

    Intended to be used as a base class for serializer for property resource
    exposed via separate endpoint.

    We consider Property as a model of the following structure:

    class Property(model):
        parent_model: ForeignKey(...)
        name = CharField()
        value = CharField()

    After converting collection of properties to representation we'll get the
    following dict:

    {
        prop1.name: prop1.value,
        prop2.name: prop2.value,
        ....
    }

    And an input dictionary of the above structure will be converted to
    the collection of Property instances
    """

    _options_class = PropertySerializerOptions

    def __init__(self, *args, **kwargs):
        super(PropertySerializer, self).__init__(*args, **kwargs)
        self.opts = self._options_class(self.Meta)

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ListToDictSerializer(*args, **kwargs)

    def get_value(self, dictionary):
        return {self.instance.name: self._get_value(
            dictionary[self.instance.field_name])}

    @cached_property
    def data(self):
        return {self.instance.name: self._get_value(self.instance)}

    def _get_value(self, obj):
        if obj.name in self.opts.json_props:
            return json.loads(obj.value)
        return obj.value

    def create(self, validated_data):
        self._meta.model.create(**validated_data)

    def update(self, obj, validated_data):
        filters = {
            parent_obj_field: getattr(obj, parent_obj_field),
            'name': obj.name
        }
        model.objects.filter(**filters).update(value=obj.value)

    def to_internal_value(self, data):
        name, value = data.iteritems().next()
        # Deal with JSON properties
        if name in self.opts.json_props:
            value = json.dumps(value)

        data = {'name': name, 'value': value}
        data = self._to_internal_value_hook(data)
        return super(PropertySerializer, self).to_internal_value(data)

    def _to_internal_value_hook(self, data):
        # Update created property with reference to parent object
        parent_obj_field = self.opts.parent_obj_field
        parent_id_field = parent_obj_field + '_id'
        data[parent_obj_field] = self.context['view'].kwargs[parent_id_field]
        return data


class NestedPropertySerializer(PropertySerializer):
    """Version of PropertySerializer for nested resources

    Intended to be used as a base class for serializer for property resource
    exposed as a nested resource.
    """
    _options_class = NestedPropertySerializerOptions
