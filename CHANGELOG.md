# [Changelog](https://github.com/yola/drf-madprops)

## 1.3.0
* Upgrade to Django 4.2.16 to resolve security issues

## 1.2.0
* Support Django 4.2 and DRF 3.15
* Remove unnecessary translation of error messages

## 1.1.0
* Dropped Python 2.6 support
* Added Python 3 support
* The new version is compatible with Django 1.11 - 3.2, DRF 3.5 - 3.12

## 1.0.0
* The new version is compatible with Django < 1.12 and DRF < 3.6.0

## 0.2.5
* Add validation of serialized data to ensure dict-ness

## 0.2.4
* Fix bug when saving properties if no properties were passed to the serializer

## 0.2.3
* Introduced NestedPropertySerializer class, which should be used for nested
  properties case.

## 0.2.2
* Fixed wrong write for nested properties case.

## 0.2.1
* New version for DRF 3.x

## 0.1.6
* Support validation on property updates

## 0.1.5
* Support validation on property creation

## 0.1.4
* Fix update for the case when self.object is an empty queryset

## 0.1.3
* Move JSON serialization to `from_native` method

## 0.1.2
* Support JSON properties

## 0.1.1
* Handle edge cases when object might be `None` in `data` and `field_to_native`
attributes of `PropertySerializer` (those cases occur when browsable APIs
are used).

## 0.1.0
* Rename `PropertiesSerializer` to `PropertySerializer` and
`NestedPropertiesSerializer` to `NestedPropertySerializer` - because we
usually use resource names in singular form.

## 0.0.1
* Initial version. Fix `_options_class` for `NestedPropertiesSerializer`
