# drf-madprops

DRF library of helpers to operate on lists of resource properties as dicts

Written and used by the folks at Yola to support our [free website builder][1].

## Overview

It's a typical case for relational DBs when some table (e.g. User) is
extended via subordinate key-value table (e.g. UserPreference). This allows
to dynamically add/delete fields to User (stored in UserPreference).
Usually those property models have very simple structures, e.g:

```python
class UserPreference(models.Model):
    id = models.AutoField()
    user = models.ForeignKey(User, related_name='preferences')
    name = models.CharField()
    value = models.CharField)
```

But it's not very convenient to expose/operate on them via standard DRF
serializers.  We'll get something like:

```json
[
    {"id": "id1", "user": "user1", "name": "property1", "value": "value1"},
    {"id": "id2", "user": "user1", "name": "property2", "value": "value2"}
    ...
]
```

This library contains two base classes for property's serializers (for cases
when properties are exposed as separate resource and as nested resource) which
allows to retrieve/operate on parent resource properties as dicts. For example,
instead of representation listed above, we'll get something like:

```json
{
    "property1": "value1",
    "property2": "value2",
    ...
}
```

## Usage

### Additional meta options

- `parent_obj_field`: field name in your `Property` model which contains
  reference to parent object. For `PropertiesSerializer` it's also used to
  calculate view params containing parent object id.

- `read_only_props`: list of property names, which values cannot be changed
  via serializer.

### As a nested serializer

```python
from madprops.serializers import NestedPropertiesSerializer


class PreferenceSerializer(NestedPropertiesSerializer):
    class Meta:
        model = Preference
        parent_obj_field = 'user'
        read_only_props = ('user_token', 'tutorial_email_sent')


class UserSerializer(ModelSerializer):
    preferences = PreferenceSerializer(many=True, required=False)
```

### As a serializer used for properties endpoint
```python
from madprops.serializers import PropertiesSerializer


class PreferenceSerializer(PropertiesSerializer):
    class Meta:
        model = Preference
        parent_obj_field = 'user'
        read_only_props = ('user_token', 'tutorial_email_sent')


class PreferencePrivateViewSet(ModelViewSet):
    serializer_class = PreferenceSerializer
    paginate_by = None
```

## Testing

Install development requirements:

    pip install -r requirements.txt

Run the tests with:

    nosetests


[1]:https://www.yola.com/
