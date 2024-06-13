## Description

Class to store Period fields


## Methods

### Public Methods

* [`PeriodFieldDefinition$new()`](#method-PeriodFieldDefinition-new)
* [`PeriodFieldDefinition$is_allowed()`](#method-PeriodFieldDefinition-is_allowed)
* [`PeriodFieldDefinition$clone()`](#method-PeriodFieldDefinition-clone)

<a id="method-PeriodFieldDefinition-new"></a>
### Method `new()`

Creates a new instance of the PeriodFieldDefinition Class


<b>Usage</b>

```r
PeriodFieldDefinition$new(name, description)
```

<b>Arguments:</b>

* `name` Character. Name of the field.
* `description` Character. Description of the field


<a id="method-PeriodFieldDefinition-is_allowed"></a>
### Method `is_allowed()`

Tests if cell is allowed


<b>Usage</b>

```r
PeriodFieldDefinition$is_allowed(cell)
```

<b>Arguments:</b>

* `cell` cell to test


<a id="method-PeriodFieldDefinition-clone"></a>
### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
PeriodFieldDefinition$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


