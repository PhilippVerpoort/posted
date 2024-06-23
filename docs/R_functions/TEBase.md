## `TEBase`
### Description

This is the base class for technoeconomic data.


### Examples

```r
## Example usage:
base_technoeconomic_data <- TEBase$new("variable_name")
```

### Methods

#### Public Methods

* [`TEBase$new()`](#method-TEBase-new)
* [`TEBase$clone()`](#method-TEBase-clone)

<a id="method-TEBase-new"></a>
#### Method `new()`

Create new instance of TEBase class. Set parent variable and technology specifications (var_specs) from input


<b>Usage</b>

```r
TEBase$new(parent_variable)
```

<b>Arguments:</b>

* `parent_variable` (`character`) Name of the parent variable


<a id="method-TEBase-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
TEBase$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


