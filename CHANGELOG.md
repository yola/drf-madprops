# [Changelog](https://github.com/yola/drf-madprops)

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
