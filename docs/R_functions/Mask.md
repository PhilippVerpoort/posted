## `Mask`
### Description

Class to define masks with conditions and weights to apply to DataFiles


### Methods

#### Public Methods

* [`Mask$new()`](#method-Mask-new)
* [`Mask$matches()`](#method-Mask-matches)
* [`Mask$get_weights()`](#method-Mask-get_weights)
* [`Mask$clone()`](#method-Mask-clone)

<a id="method-Mask-new"></a>
#### Method `new()`

Create a new mask object


<b>Usage</b>

```r
Mask$new(where = NULL, use = NULL, weight = NULL, other = NaN, comment = "")
```

<b>Arguments:</b>

* `where` MaskCondition | list[MaskCondition](./MaskCondition), optional. Where the mask should be applied.
* `use` MaskCondition | list[MaskCondition](./MaskCondition), optional. Condition on where to use the masks.
* `weight` Numeric | Character | list[Numeric | Character](./Numeric | Character), optional. Weights to apply.
* `other` Numeric, optional.
* `comment` Character, optional. Comment.


<a id="method-Mask-matches"></a>
#### Method `matches()`

Check if a mask matches a dataframe by verifying if all 'where' conditions match across all rows.


<b>Usage</b>

```r
Mask$matches(df)
```

<b>Arguments:</b>

* `df` DataFrame. Dataframe to check for matches.


<b>Returns:</b>


Logical. If the mask matches the dataframe.


<a id="method-Mask-get_weights"></a>
#### Method `get_weights()`

Apply weights to the dataframe


<b>Usage</b>

```r
Mask$get_weights(df)
```

<b>Arguments:</b>

* `df` (`Dataframe`): Dataframe to apply weights on


<b>Returns:</b>


Dataframe. Dataframe with applied weights


<a id="method-Mask-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
Mask$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


