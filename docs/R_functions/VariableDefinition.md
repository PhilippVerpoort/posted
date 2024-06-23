## `VariableDefinition`
### Description

Class to store variable columns


### Methods

#### Public Methods

* [`VariableDefinition$new()`](#method-VariableDefinition-new)
* [`VariableDefinition$is_allowed()`](#method-VariableDefinition-is_allowed)
* [`VariableDefinition$clone()`](#method-VariableDefinition-clone)

<a id="method-VariableDefinition-new"></a>
#### Method `new()`

Creates a new instance of the VariableDefinition class


<b>Usage</b>

```r
VariableDefinition$new(name, description, required)
```

<b>Arguments:</b>

* `name` (`Character`): Name of the column.
* `description` (`Character`): Description of the column.
* `required` (`Logical`): Bool that specifies if the column is required.


<a id="method-VariableDefinition-is_allowed"></a>
#### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
VariableDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-VariableDefinition-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
VariableDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


