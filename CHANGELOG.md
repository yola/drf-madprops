# [Changelog](https://github.com/yola/drf-madprops)

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
