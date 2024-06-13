## Description

This class is used to store Technoeconomic DataFiles.


## Examples

```r
# Example usage:
tedf <- TEDF$new("variable_name")
tedf$load()
tedf$read("file_path.csv")
tedf$write("output_file_path.csv")
tedf$check()
tedf$check_row()


## ------------------------------------------------
## Method `TEDF$load`
## ------------------------------------------------

# Example usage:
tedf$load()


## ------------------------------------------------
## Method `TEDF$read`
## ------------------------------------------------

# Example usage:
tedf$read()


## ------------------------------------------------
## Method `TEDF$write`
## ------------------------------------------------

# Example usage:
tedf$write()


## ------------------------------------------------
## Method `TEDF$check`
## ------------------------------------------------

# Example usage:
tedf$check(raise_exception = TRUE)
```

## Methods

### Public Methods

* [`TEDF$new()`](#method-TEDF-new)
* [`TEDF$load()`](#method-TEDF-load)
* [`TEDF$read()`](#method-TEDF-read)
* [`TEDF$write()`](#method-TEDF-write)
* [`TEDF$check()`](#method-TEDF-check)
* [`TEDF$check_row()`](#method-TEDF-check_row)
* [`TEDF$clone()`](#method-TEDF-clone)

<a id="method-TEDF-new"></a>
### Method `new()`

Create new instance of TEDF class. Initialise parent class and object fields


<b>Usage</b>

```r
TEDF$new(
  parent_variable,
  database_id = "public",
  file_path = NULL,
  data = NULL
)
```

<b>Arguments:</b>

* `parent_variable` (`Character`): Variable from which data should be collected.
* `database_id` (`Character`):, default: "public". Database from which to load data.
* `file_path` (`Path`):, optional. File path from which to load file.
* `data` (`DataFrame`):, optional. Specific Technoeconomic data.


<a id="method-TEDF-load"></a>
### Method `load()`

Load TEDataFile (only if it has not been read yet)


<b>Usage</b>

```r
TEDF$load()
```

<b>Example:</b>

```r
# Example usage:
tedf$load()
```

<b>Returns:</b>


TEDF. Returns the TEDF object it is called on.


<a id="method-TEDF-read"></a>
### Method `read()`

This method reads TEDF from a CSV file.


<b>Usage</b>

```r
TEDF$read()
```

<b>Example:</b>

```r
# Example usage:
tedf$read()
```

<a id="method-TEDF-write"></a>
### Method `write()`

write TEDF to CSV file.


<b>Usage</b>

```r
TEDF$write()
```

<b>Example:</b>

```r
# Example usage:
tedf$write()
```

<a id="method-TEDF-check"></a>
### Method `check()`

Check that TEDF is consistent and add inconsistencies to internal parameter


<b>Usage</b>

```r
TEDF$check(raise_exception = TRUE)
```

<b>Arguments:</b>

* `raise_exception` Logical, default: TRUE. If an exception is to be raised.


<b>Example:</b>

```r
# Example usage:
tedf$check(raise_exception = TRUE)
```

<a id="method-TEDF-check_row"></a>
### Method `check_row()`

checks if row of dataframe has issues


<b>Usage</b>

```r
TEDF$check_row(row_id, raise_exception = TRUE)
```

<b>Arguments:</b>

* `row_id` Id of the row
* `raise_exception` (`logical`) If exception is to be raised


<a id="method-TEDF-clone"></a>
### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
TEDF$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


