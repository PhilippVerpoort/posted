# `normalise_units`

normalise_units

## Description

Takes a DataFrame with reported or reference data, along with
dictionaries mapping variable units and flow IDs, and normalizes the units of the variables in the
DataFrame based on the provided mappings.


## Usage

```r
normalise_units(df, level, var_units, var_flow_ids)
```

## Arguments

Argument      |Description
------------- |----------------
`df` | DataFrame. Dataframe to be normalized.
`level` | Character. Specifies whether the data should be normalized on the reported or reference values. Possible values are 'reported' or 'reference'.
`var_units` | List. Dictionary that maps a combination of parent variable and variable to its corresponding unit. The keys in the dictionary are in the format "{parent_variable}|{variable}", and the values are the units associated with that variable.
`var_flow_ids` | List. Dictionary that maps a combination of parent variable and variable to a specific flow ID. This flow ID is used for unit conversion in the `normalize_units` function.

## Return Value

DataFrame. Normalized dataframe.


## Examples

```r
# Example usage:
normalize_dataframe(df, "reported", var_units, var_flow_ids)
```

