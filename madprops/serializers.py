from collections import Iterable

from django.db.models import ForeignKey
from django.utils.functional import cached_property
from rest_framework.serializers import (
    ModelSerializer, ModelSerializerOptions, RelationsList)


class PropertiesSerializerOptions(ModelSerializerOptions):
    """Meta class options for PropertiesSerializer"""
    def __init__(self, meta):
        super(PropertiesSerializerOptions, self).__init__(meta)
        self.read_only_props = getattr(meta, 'read_only_props', [])
        self.exclude = ('id',)

    @cached_property
    def parent_obj_field(self):
        # Automagically get the name of field containing relation to parent
        for field in self.model._meta.fields:
            if isinstance(field, ForeignKey):
                return field.name

        raise ValueError(
            '{0} misses relation to parent model'.format(self.model))


class NestedPropertiesSerializerOptions(PropertiesSerializerOptions):
    """Meta class options for NestedPropertiesSerializer"""
    def __init__(self, meta):
        super(NestedPropertiesSerializerOptions, self).__init__(meta)
        self.exclude = ('id', self.parent_obj_field)


class PropertiesSerializer(ModelSerializer):
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

    _options_class = PropertiesSerializerOptions

    def field_to_native(self, obj, field_name):
        return self._to_representation(getattr(obj, field_name).all())

    @cached_property
    def data(self):
        return self._to_representation(self.objects)

    def _to_representation(self, objects):
        return dict((obj.name, obj.value) for obj in objects)

    @cached_property
    def errors(self):
        if not isinstance(self.init_data, dict):
            return {'non_field_errors': ['Expected a dictionary.']}

        # Ensure we don't modify read-only properties.  Remove them from input.
        for prop in self.opts.read_only_props:
            self.init_data.pop(prop, None)

        if self.object:
            return self._update()

        return self._create()

    def _create(self):
        self.object = RelationsList(
            self.from_native({k: v}) for k, v in self.init_data.iteritems()
        )

    def _update(self):
        result = RelationsList()
        existent_props = dict((obj.name, obj) for obj in self.objects)
        # Set object to None, because it's used in other methods and
        # might break them.
        self.object = None
        for name, value in self.init_data.iteritems():
            existent_prop = existent_props.get(name)
            if existent_prop is not None:
                existent_prop.value = value
                result.append(existent_prop)
            else:
                result.append(self.from_native({name: value}))
        self.object = result

    def from_native(self, data, files=None):
        name, value = data.iteritems().next()
        data = {'name': name, 'value': value}

        # Update created property with reference to parent object
        parent_obj_field = self.opts.parent_obj_field
        parent_id_field = parent_obj_field + '_id'
        data[parent_obj_field] = self.context['view'].kwargs[parent_id_field]

        return super(PropertiesSerializer, self).from_native(data, files)

    @property
    def objects(self):
        # Ensure we always work with iterable
        if isinstance(self.object, Iterable):
            return self.object
        return [self.object]

    def save_object(self, obj, **kwargs):
        # Ensure we have only one property with the same name
        model = self.opts.model
        parent_obj_field = self.opts.parent_obj_field
        filters = {
            parent_obj_field: getattr(obj, parent_obj_field),
            'name': obj.name
        }
        if not model.objects.filter(**filters).update(value=obj.value):
            obj.save(**kwargs)


class NestedPropertiesSerializer(PropertiesSerializer):
    """Version of PropertiesSerializer for nested resources

    Intended to be used as a base class for serializer for property resource
    exposed as a nested resource.
    """

    _options_class = PropertiesSerializerOptions

    def from_native(self, data, files=None):
        name, value = data.iteritems().next()
        return super(PropertiesSerializer, self).from_native(
            {'name': name, 'value': value}, files)
