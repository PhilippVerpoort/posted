## `normalise_values`

normalise_values

### Description

Takes a DataFrame as input, normalizes the 'value' and 'uncertainty'
columns by the reference value, and updates the 'reference_value' column accordingly.


### Usage

```r
normalise_values(df)
```

### Arguments

Argument      |Description
------------- |----------------
`df` | DataFrame. Dataframe to be normalized.

### Return Value

DataFrame. Returns a modified DataFrame where the 'value' column has been
divided by the 'reference_value' column (or 1.0 if 'reference_value' is null), the 'uncertainty'
column has been divided by the 'reference_value' column, and the 'reference_value' column has been
replaced with 1.0 if it was not null.


### Examples

```r
## Example usage:
normalized_df <- normalize_values(df)
```

