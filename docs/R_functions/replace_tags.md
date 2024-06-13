# `replace_tags`

replace_tags

## Description

Replaces specified tags in dictionary keys and values with corresponding
items from another dictionary.


## Usage

```r
replace_tags(definitions, tag, items)
```

## Arguments

Argument      |Description
------------- |----------------
`definitions` | List. Dictionary containing the definitions, where the tags should be replaced by the items.
`tag` | Character. String to identify where replacements should be made in the definitions. Specifies the placeholder that needs to be replaced with actual values from the `items` dictionary.
`items` | List. Dictionary containing the items from which to replace the definitions.

## Return Value

List. Dictionary containing the definitions with replacements based on the provided tag and items.


