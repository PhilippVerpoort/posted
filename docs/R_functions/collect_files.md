# `collect_files`

collect_files

## Description

Takes a parent variable and optional list of databases to include,
checks for their existence, and collects files and directories based on the parent variable.


## Usage

```r
collect_files(parent_variable, include_databases = NULL)
```

## Arguments

Argument      |Description
------------- |----------------
`parent_variable` | Character. Variable to collect files on.
`include_databases` | Optional list[Character](./Character). List of Database IDs to collect files from.

## Return Value

List of tuples. List of tuples containing the parent variable and the
database ID for each file found in the specified directories.


## Examples

```r
# Example usage:
collect_files("variable_name", c("db1", "db2"))
```

