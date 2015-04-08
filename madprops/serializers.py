from django.utils.functional import cached_property
from rest_framework.serializers import (
    ModelSerializer, ModelSerializerOptions, RelationsList)


class PropertiesSerializerOptions(ModelSerializerOptions):
    """Meta class options for PropertiesSerializer"""
    def __init__(self, meta):
        super(PropertiesSerializerOptions, self).__init__(meta)
        self.parent_obj_name = getattr(meta, 'parent_obj_name', None)
        self.read_only_props = getattr(meta, 'read_only_props', [])
        self.exclude = ('id',)


class NestedPropertiesSerializerOptions(PropertiesSerializerOptions):
    """Meta class options for NestedPropertiesSerializer"""
    def __init__(self, meta):
        super(NestedPropertiesSerializerOptions, self).__init__(meta)
        self.exclude = ('id', self.parent_obj_name)


class PropertiesSerializer(ModelSerializer):
    """Allows to operate properties of certain resource as dictionary

    Intended to be used as a base class for serializer for property resource
    exposed via separate endpoint.

    to representation:
        many objects -> {obj1.name: obj1.value, obj2.name: obj2.value ...}
        object -> {'value': obj.value}

    to internal value:
        {name: value} -> obj.name = name, obj.value = value
        {name1: value1, name2: value2 ...} -> obj1, obj2 ...
    """

    _options_class = PropertiesSerializerOptions

    def field_to_native(self, obj, field_name):
        return dict((p.name, p.value) for p in getattr(obj, field_name).all())

    @cached_property
    def errors(self):
        if not isinstance(self.init_data, dict):
            return {'non_field_errors': ['Expected a dictionary.']}

        # Remove read-only properties
        for prop in self.opts.read_only_props:
            self.init_data.pop(prop, None)

        if self.object:
            return self._update()

        return self._create()

    def _update(self):
        if self.many:
            return self._update_many()

        if 'value' in self.init_data:
            self.object.value = self.init_data['value']

    def _create(self):
        if self.many:
            self.object = RelationsList(
                self.from_native({k: v}) for k, v in self.init_data.iteritems()
            )
        else:
            self.object = self.from_native(self.init_data)

    def _update_many(self):
        result = RelationsList()
        existent_props = dict((obj.name, obj) for obj in self.object)
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
        parent_obj_name = self.opts.parent_obj_name
        parent_id_name = parent_obj_name + '_id'
        data[parent_obj_name] = self.context['view'].kwargs[parent_id_name]

        return super(PropertiesSerializer, self).from_native(data, files)

    @cached_property
    def data(self):
        if self.many:
            return dict((pref.name, pref.value) for pref in self.object)
        return {'value': self.object.value}

    def save_object(self, obj, **kwargs):
        # Ensure we have only one property with the same name
        model = self.opts.model
        parent_obj_name = self.opts.parent_obj_name
        filters = {
            parent_obj_name: getattr(obj, parent_obj_name),
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
