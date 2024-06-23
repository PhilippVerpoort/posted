## `UnitDefinition`
### Description

Class to store Unit columns


### Methods

#### Public Methods

* [`UnitDefinition$new()`](#method-UnitDefinition-new)
* [`UnitDefinition$is_allowed()`](#method-UnitDefinition-is_allowed)
* [`UnitDefinition$clone()`](#method-UnitDefinition-clone)

<a id="method-UnitDefinition-new"></a>
#### Method `new()`

Creates a new instance of the UnitDefinition class


<b>Usage</b>

```r
UnitDefinition$new(name, description, required)
```

<b>Arguments:</b>

* `name` Character. Name of the column.
* `description` Character. Description of the column.
* `required` Logical. Bool that specifies if the column is required.


<a id="method-UnitDefinition-is_allowed"></a>
#### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
UnitDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-UnitDefinition-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
UnitDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


