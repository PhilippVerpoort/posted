# `read_definitions`

read_definitions

## Description

Reads YAML files from definitions directory, extracts tags, inserts tags into
definitions, replaces tokens in definitions, and returns the updated definitions.


## Usage

```r
read_definitions(definitions_dir, flows, techs)
```

## Arguments

Argument      |Description
------------- |----------------
`definitions_dir` | Character. Path leading to the definitions.
`flows` | List. Dictionary containing the different flow types. Each key represents a flow type, the corresponding value is a dictionary containing key value pairs of attributes like density, energy content and their values.
`techs` | List. Dictionary containing information about different technologies. Each key in the dictionary represents a unique technology ID, and the corresponding value is a dictionary containing various specifications for that technology, like 'description', 'class', 'primary output' etc.

## Return Value

List. Dictionary containing the definitions after processing and replacing tags and tokens.


