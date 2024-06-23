## `TEDFInconsistencyException`
### Description

This is a class to store inconsistencies in the TEDFs


### Methods

#### Public Methods

* [`TEDFInconsistencyException$new()`](#method-TEDFInconsistencyException-new)
* [`TEDFInconsistencyException$clone()`](#method-TEDFInconsistencyException-clone)

<a id="method-TEDFInconsistencyException-new"></a>
#### Method `new()`

Create instance of TEDFInconsistencyException class


<b>Usage</b>

```r
TEDFInconsistencyException$new(
  message = "Inconsistency detected",
  row_id = NULL,
  col_id = NULL,
  file_path = NULL
)
```

<b>Arguments:</b>

* `message` (`character`) the message of the exception
* `row_id` Id of the row
* `col_id` Id of the column
* `file_path` file path


<a id="method-TEDFInconsistencyException-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
TEDFInconsistencyException$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


