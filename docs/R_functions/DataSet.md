## `DataSet`
### Description

This class provides methods to store, normalize, select, and aggregate DataSets.


### Examples

```r
### ------------------------------------------------
### Method `DataSet$normalise`
### ------------------------------------------------

## Example usage:
dataset$normalize(override = list("variable1" = "value1"), inplace = FALSE)


### ------------------------------------------------
### Method `DataSet$select`
### ------------------------------------------------

## Example usage:
dataset$select(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, field1 = "value1")


### ------------------------------------------------
### Method `DataSet$aggregate`
### ------------------------------------------------

## Example usage:
dataset$aggregate(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, agg = "field", masks = list(mask1, mask2), masks_database = TRUE)
```

### Methods

#### Public Methods

* [`DataSet$new()`](#method-DataSet-new)
* [`DataSet$normalise()`](#method-DataSet-normalise)
* [`DataSet$select()`](#method-DataSet-select)
* [`DataSet$aggregate()`](#method-DataSet-aggregate)
* [`DataSet$clone()`](#method-DataSet-clone)

<a id="method-DataSet-new"></a>
#### Method `new()`

Create new instance of the DataSet class


<b>Usage</b>

```r
DataSet$new(
  parent_variable,
  include_databases = NULL,
  file_paths = NULL,
  check_inconsistencies = FALSE,
  data = NULL
)
```

<b>Arguments:</b>

* `parent_variable` Character. Variable to collect Data on.
* `include_databases` Optional list[Character](./Character) | tuple[Character](./Character), optional. Databases to load from.
* `file_paths` Optional list[Character](./Character), optional. Paths to load data from.
* `check_inconsistencies` Logical, optional. Whether to check for inconsistencies.
* `data` Optional DataFrame, optional. Specific data to include in the dataset.


<a id="method-DataSet-normalise"></a>
#### Method `normalise()`

Normalize data: default reference units, reference value equal to 1.0, default reported units


<b>Usage</b>

```r
DataSet$normalise(override = NULL, inplace = FALSE)
```

<b>Arguments:</b>

* `override` Optional list[Character](./Character). Dictionary with key, value pairs of variables to override.
* `inplace` Logical, optional. Whether to do the normalization in place.


<b>Example:</b>

```r
## Example usage:
dataset$normalize(override = list("variable1" = "value1"), inplace = FALSE)
```

<b>Returns:</b>


DataFrame. If `inplace` is `FALSE`, returns normalized dataframe.


<a id="method-DataSet-select"></a>
#### Method `select()`

Select desired data from the dataframe


<b>Usage</b>

```r
DataSet$select(
  override = NULL,
  drop_singular_fields = TRUE,
  extrapolate_period = TRUE,
  ...
)
```

<b>Arguments:</b>

* `override` Optional list[Character](./Character). Dictionary with key, value pairs of variables to override.
* `drop_singular_fields` Logical, optional. If `TRUE`, drop custom fields with only one value.
* `extrapolate_period` Logical, optional. If `TRUE`, extrapolate values if no value for this period is given.
* `...` IDs of values to select.


<b>Example:</b>

```r
## Example usage:
dataset$select(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, field1 = "value1")
```

<b>Returns:</b>


DataFrame. DataFrame with selected values.


<a id="method-DataSet-aggregate"></a>
#### Method `aggregate()`

Aggregates data based on specified parameters, applies masks,
and cleans up the resulting DataFrame.


<b>Usage</b>

```r
DataSet$aggregate(
  override = NULL,
  drop_singular_fields = TRUE,
  extrapolate_period = TRUE,
  agg = NULL,
  masks = NULL,
  masks_database = TRUE,
  ...
)
```

<b>Arguments:</b>

* `override` Optional list[Character](./Character). Dictionary with key, value pairs of variables to override.
* `drop_singular_fields` Logical, optional. If `TRUE`, drop custom fields with only one value.
* `extrapolate_period` Logical, optional. If `TRUE`, extrapolate values if no value for this period is given.
* `agg` Optional Character | list[Character](./Character) | tuple[Character](./Character). Specifies which fields to aggregate over.
* `masks` Optional list[Mask](./Mask). Specifies a list of Mask objects that will be applied to the data during aggregation. These masks can be used to filter or weight the data based on certain conditions defined in the Mask objects.
* `masks_database` Logical, optional. Determines whether to include masks from databases in the aggregation process. If `TRUE`, masks from databases will be included along with any masks provided as function arguments. If `FALSE`, only the masks provided as function arguments will be applied.
* `...` additional field vals


<b>Example:</b>

```r
## Example usage:
dataset$aggregate(override = list("variable1" = "value1"), drop_singular_fields = TRUE, extrapolate_period = FALSE, agg = "field", masks = list(mask1, mask2), masks_database = TRUE)
```

<b>Returns:</b>


DataFrame. The `aggregate` method returns a pandas DataFrame that has been cleaned up and aggregated based on the specified parameters and input data. The method performs aggregation over component fields and case fields, applies weights based on masks, drops rows with NaN weights, aggregates with weights, inserts reference variables, sorts columns and rows, rounds values, and inserts units before returning the final cleaned and aggregated DataFrame.


<a id="method-DataSet-clone"></a>
#### Method `clone()`

The objects of this class are cloneable with this method.


<b>Usage</b>

```r
DataSet$clone(deep = FALSE)
```

<b>Arguments:</b>

* `deep` Whether to make a deep clone.


