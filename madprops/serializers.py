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
        self.list_serializer_class = ListToDictSerializer

    @cached_property
    def parent_obj_field(self):
        # Automagically get the name of field containing relation to parent
        for field in self.model._meta.fields:
            if isinstance(field, ForeignKey):
                return field.name

        raise ValueError(
            '{0} misses relation to parent model'.format(self.model))


class ListToDictSerializer(ListSerializer):
    default_error_messages = []

    @property
    def data(self):
        return super(ListSerializer, self).data

    def to_representation(self, value):
        # Since this is ListSerializer, it makes everything a list. We need
        # dict (<name>: <value>}, so convert it to dictionary.
        result_list = super(
            ListToDictSerializer, self).to_representation(value)

        result_dict = {}
        for pair in result_list:
            result_dict.update(pair)

        return result_dict

    def to_internal_value(self, data):
        data_list = []
        for (prop_name, prop_value) in data.items():
            data_list.append({'name': prop_name, 'value': prop_value})
        return super(ListToDictSerializer, self).to_internal_value(data_list)

    def save(self):
        return [
            self.child.save(property_data) for data in self.validated_data
        ]


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
        self.Meta.list_serializer_class = ListToDictSerializer

    def to_representation(self, data):
        if isinstance(data, dict):
            return {data['name']: self._get_value(data)}
        else:
            return {data.name: self._get_value({'name': data.name, 'value': data.value})}

    def _get_value(self, data):
        if data['name'] in self.opts.json_props:
            return json.loads(data['value'])
        return data['value']

    def save(self, property_data=None):
        property_data = property_data or self.validated_data
        prop_name = property_data['name']

        if prop_name in self.opts.read_only_props:
            return prop

        # Try to find property by it's name.
        parent_obj_field = self.opts.parent_obj_field
        filters = {
            parent_obj_field: property_data[parent_obj_field],
            'name': prop_name
        }

        # If it already exists - update it's value. Otherwise - create a new
        # property.
        prop = self.Meta.model.objects.filter(**filters).first()
        if prop:
            prop.value=property_data['value']
            prop.save()
        else:
            prop = self.Meta.model.objects.create(**property_data)

        return prop

    def to_internal_value(self, data):
        # Data can be in two formats here depending on many=True/False:
        #   - {<prop_name>: <prop_value>}
        #   - {'name': <prop_name>, 'value': <prop_value>}
        # Convert to the format accepted by standard DRF serializers.
        if not('name' in data and 'value' in data):
            data = self._to_extended_dict(data)

        # Handle JSON fields (value encoded as JSON).
        if data['name'] in self.opts.json_props:
            data['value'] = json.dumps(data['value'])

        data = self._add_parent_obj_field(data)
        return super(PropertySerializer, self).to_internal_value(data)

    def _to_extended_dict(self, data):
        """ Convert dictionary of properties:
        {<prop_name>: <prop_value>} ->
            {'name': <prop_name>, 'value': <prop_value>}
        """
        prop_name, prop_value = data.items()[0]
        return {'name': prop_name, 'value': prop_value}

    def _add_parent_obj_field(self, data):
        # Property requires ID of parent object (properties owner, e.g. User
        # for user's properties case). Take it from context, which is passed
        # from view.
        parent_obj_field = self.opts.parent_obj_field
        parent_id_field = parent_obj_field + '_id'
        data[parent_obj_field] = self.context.get('parent_id',
            self.context['view'].kwargs[parent_id_field])
        return data


class PropertiesOwnerSerializer(ModelSerializer):
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if isinstance(self.fields[attr], ListToDictSerializer):
                self._save_properties(instance, attr)
                continue
            setattr(instance, attr, value)
        instance.save()

        return instance

    def _save_properties(self, instance, field_name):
        data_dict = self._data_list_to_dict(self.validated_data[field_name])
        properties_serializer = self.fields[field_name].child.__class__
        serializer = properties_serializer(data=data_dict, many=True)
        serializer.is_valid()
        serializer.save()

    def _data_list_to_dict(self, properties_list):
        properties_dict = {}
        for property in properties_list:
            properties_dict[property['name']] = property['value']

        return properties_dict
