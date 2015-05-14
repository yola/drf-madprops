import json

from django.db.models import ForeignKey
from rest_framework.utils import model_meta
from django.utils.functional import cached_property
from rest_framework.serializers import ListSerializer, ModelSerializer


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
    """This is how the DRF 3.0 works. For many=True case it automatically
    returns a "List" serializer instead of original one
    (__new__ method is overriden). Thus, we need to teach it to work with
    {<prop_name>: <prop_value>,...} dict instead of standard
    [{'name': <prop_name>, 'value': <prop_value>}...].
    """
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
            self.child.save(property_data)
            for property_data in self.validated_data
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
            return {data.name: self._get_value(
                {'name': data.name, 'value': data.value})}

    def _get_value(self, data):
        if data['name'] in self.opts.json_props:
            return json.loads(data['value'])
        return data['value']

    def save(self, property_data=None):
        property_data = property_data or self.validated_data
        prop_name = property_data['name']

        # Try to find property by it's name.
        parent_obj_field = self.opts.parent_obj_field
        filters = {
            parent_obj_field: property_data[parent_obj_field],
            'name': prop_name
        }

        # If it already exists - update it's value. Otherwise - create a new
        # property.
        prop = self.Meta.model.objects.filter(**filters).first()

        if prop_name in self.opts.read_only_props:
            return prop

        if prop:
            prop.value = property_data['value']
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
        data[parent_obj_field] = self.context.get(
            'parent_id') or self.context['view'].kwargs.get(
                parent_id_field)
        return data


class PropertiesOwnerSerializer(ModelSerializer):
    """Since we need to support nested writable fields, but DRF 3.0 doesn't
    support this, we have to use this class as a base class for parent model
    serialization.
    """
    def create(self, validated_data):
        """ Code copied from DRF. Removed check for nested writes, added
        preferences save.
        """
        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            instance = ModelClass.objects.create(**validated_data)
        except TypeError as exc:
            msg = (
                'Got a `TypeError` when calling `%s.objects.create()`. '
                'This may be because you have a writable field on the '
                'serializer class that is not a valid argument to '
                '`%s.objects.create()`. You may need to make the field '
                'read-only, or override the %s.create() method to handle '
                'this correctly.\nOriginal exception text was: %s.' %
                (
                    ModelClass.__name__,
                    ModelClass.__name__,
                    self.__class__.__name__,
                    exc
                )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                if isinstance(self.fields[field_name], ListToDictSerializer):
                    self._save_properties(instance, field_name)
                    continue
                setattr(instance, field_name, value)

        return instance

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
        # Get correct serializer class.
        properties_serializer_class = self.fields[field_name].child.__class__
        # We can't pass parent ID using View callback like we do for edits.
        # So we pass parent_id directly.
        serializer = properties_serializer_class(
            data=data_dict, many=True, context={'parent_id': instance.pk})
        serializer.is_valid()

        serializer.save()

    def _data_list_to_dict(self, properties_list):
        """[{'name': <prop_name>, 'value': <prop_value>},...] ->
        {<prop_name>: <prop_value>,...}
        """
        properties_dict = {}
        for property in properties_list:
            properties_dict[property['name']] = property['value']


        return properties_dict
