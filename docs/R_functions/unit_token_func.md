## `unit_token_func`

unit_token_func

### Description

Takes a unit component type and a dictionary of flows, and returns a lambda function
that extracts the default unit based on the specified component type from the flow
dictionary.


### Usage

```r
unit_token_func(unit_component, flows)
```

### Arguments

Argument      |Description
------------- |----------------
`unit_component` | Character. Specifies the type of unit token to be returned. Possible values are 'full', 'raw', 'variant'.
`flows` | List. Dictionary containing the flows.

### Return Value

Function. Lambda function that takes a dictionary `def_specs` as input. The lambda function
will return different values based on the `unit_component` parameter.


