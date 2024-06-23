## `AbstractFieldDefinition`
### Description

Abstract class to store fields


### Examples

```r
### ------------------------------------------------
### Method `AbstractFieldDefinition$select_and_expand`
### ------------------------------------------------

## Example usage:
## select_and_expand(df, "col_id", field_vals = NULL)
```

### Methods

#### Public Methods

* [`AbstractFieldDefinition$new()`](#method-AbstractFieldDefinition-new)
* [`AbstractFieldDefinition$is_allowed()`](#method-AbstractFieldDefinition-is_allowed)
* [`AbstractFieldDefinition$select_and_expand()`](#method-AbstractFieldDefinition-select_and_expand)
* [`AbstractFieldDefinition$clone()`](#method-AbstractFieldDefinition-clone)

<a id="method-AbstractFieldDefinition-new"></a>
#### Method `new()`

Creates a new instance of the AbstractFieldDefinition Class


<b>Usage</b>

```r
AbstractFieldDefinition$new(
  field_type,
  name,
  description,
  dtype,
  coded,
  codes = NULL
)
```

<b>Arguments:</b>

* `field_type` Type of the field
* `name` Name of the field
* `description` Description of the field
* `dtype` Data type of the field
* `coded` If the field is coded
* `codes` Optional codes for the field (default: NULL)


<a id="method-AbstractFieldDefinition-is_allowed"></a>
#### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
AbstractFieldDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-AbstractFieldDefinition-select_and_expand"></a>
#### Method `select_and_expand()`

Select and expand fields which are valid for multiple periods or other field vals


<b>Usage</b>

```r
AbstractFieldDefinition$select_and_expand(df, col_id, field_vals = NA, ...)
```

<b>Arguments:</b>

* `df` DataFrame where fields should be selected and expanded
* `col_id` col_id of the column to be selected and expanded
* `field_vals` NULL or list of field_vals to select and expand
* `...` Additional keyword arguments


<b>Example:</b>

```r
## Example usage:
## select_and_expand(df, "col_id", field_vals = NULL)
```

<b>Returns:</b>


DataFrame where fields are selected and expanded


<a id="method-AbstractFieldDefinition-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
AbstractFieldDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


