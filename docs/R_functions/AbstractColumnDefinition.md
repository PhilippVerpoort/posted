## Description

Abstract class to store columns


## Methods

### Public Methods

* [`AbstractColumnDefinition$new()`](#method-AbstractColumnDefinition-new)
* [`AbstractColumnDefinition$is_allowed()`](#method-AbstractColumnDefinition-is_allowed)
* [`AbstractColumnDefinition$clone()`](#method-AbstractColumnDefinition-clone)

<a id="method-AbstractColumnDefinition-new"></a>
### Method `new()`

Creates a new instance of the AbstractColumnDefinition class


<b>Usage</b>

```r
AbstractColumnDefinition$new(col_type, name, description, dtype, required)
```

<b>Arguments:</b>

* `col_type` (`data.frame`)\cr Type of the column.
* `name` (`character(1)`)\cr Name of the column.
* `description` (`character(1)`)\cr Description of the column.
* `dtype` (\verb{Data type})\cr Data type of the column.
* `required` (`Logical`)\cr Bool that specifies if the column is required.


<a id="method-AbstractColumnDefinition-is_allowed"></a>
### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
AbstractColumnDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-AbstractColumnDefinition-clone"></a>
### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
AbstractColumnDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


