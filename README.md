# drf-madprops [![Build Status](https://travis-ci.com/yola/drf-madprops.svg?branch=master)](https://travis-ci.com/yola/drf-madprops)

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

- `read_only_props`: list of property names, which values cannot be changed
  via serializer.
- `json_props`: list of property names, which values are stored as JSON.
  Serializer will `json.loads()` those values when converting to representation
  and will `json.dumps()` them before saving.

### As a nested serializer

```python
from madprops.serializers import NestedPropertySerializer, PropertiesOwnerSerializer


class PreferenceSerializer(NestedPropertySerializer):
    class Meta:
        model = Preference
        read_only_props = ('user_token', 'tutorial_email_sent')
        json_props = ('packages',)


class UserSerializer(PropertiesOwnerSerializer):
    preferences = PreferenceSerializer(many=True, required=False)
```

### As a serializer used for properties endpoint
```python
from madprops.serializers import PropertySerializer


class PreferenceSerializer(PropertySerializer):
    class Meta:
        model = Preference
        read_only_props = ('user_token', 'tutorial_email_sent')


class PreferencePrivateViewSet(ModelViewSet):
    serializer_class = PreferenceSerializer
    paginate_by = None
```

## Testing

Run the tests with:

    tox

Or install development requirements and run tests with:

    pip install -r requirements.txt
    pytest tests


[1]:https://www.yola.com/
