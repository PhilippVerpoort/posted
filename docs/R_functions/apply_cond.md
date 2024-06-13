# `apply_cond`

apply_cond

## Description

Takes a pandas DataFrame and a condition, which can be a string, dictionary,
or callable, and applies the condition to the DataFrame using `eval` or `apply`
accordingly.


## Usage

```r
apply_cond(df, cond)
```

## Arguments

Argument      |Description
------------- |----------------
`df` | DataFrame. A pandas DataFrame containing the data on which the condition will be applied.
`cond` | MaskCondition. The condition to be applied on the dataframe. Can be either a string, a dictionary, or a callable function.

## Return Value

DataFrame. Dataframe evaluated at the mask condition.


