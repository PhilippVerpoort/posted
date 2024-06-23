## `ValueDefinition`
### Description

Class to store Value columns


### Methods

#### Public Methods

* [`ValueDefinition$new()`](#method-ValueDefinition-new)
* [`ValueDefinition$is_allowed()`](#method-ValueDefinition-is_allowed)
* [`ValueDefinition$clone()`](#method-ValueDefinition-clone)

<a id="method-ValueDefinition-new"></a>
#### Method `new()`

Creates a new instance of the ValueDefinition class


<b>Usage</b>

```r
ValueDefinition$new(name, description, required)
```

<b>Arguments:</b>

* `name` Character. Name of the column.
* `description` Character. Description of the column.
* `required` Logical. Bool that specifies if the column is required.


<a id="method-ValueDefinition-is_allowed"></a>
#### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
ValueDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-ValueDefinition-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
ValueDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


