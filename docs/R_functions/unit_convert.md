# `unit_convert`

Conversion of units with or withour flow ID

## Description

Converts units with optional flow context handling based on
specified variants and flow ID. The function checks if the input units are not NaN,
then it proceeds to handle different cases based on the presence of a flow context and unit
variants.


## Usage

```r
unit_convert(unit_from, unit_to, flow_id = NULL)
```

## Arguments

Argument      |Description
------------- |----------------
`unit_from` | Character or numeric. Unit to convert from.
`unit_to` | Character or numeric. Unit to convert to.
`flow_id` | Character or NULL. Identifier for the specific flow or process.

## Return Value

Numeric. Conversion factor between `unit_from` and `unit_to`.


## Examples

```r
# Example usage:
unit_convert("m", "km", flow_id = NULL)
```

