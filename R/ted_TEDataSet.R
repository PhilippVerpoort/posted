library(magrittr)

source("R/config_read_config.R")
source("R/path.R")
source("R/ted_TEDataFile.R")
#source("R/units_units.R")

#' The class that implements a fully usable TE data set.
#' 
#' @description This class implements a fully usable TE data set.
#' It enables to generate aggregated tables to analize the underlying data.
#' @examples
#' elh2 <- TEDataSet$new("elh2")
#' elh2$data()
#' @export TEDataSet
TEDataSet <- R6::R6Class("TEDataSet",
    inherit = TEBase,
    private = list(
        tid = NULL,
        load_other = NULL,
        load_database = NULL,
        check_incons = NULL,
        df = NULL,
        refUnits = NULL,
        repUnits = NULL,
        # Description
        # Load the data files from the POSTED database. Check consistency if required.
        loadFiles = function(load_other = list(), load_database, check_incons) {
            files <- list()

            # load default TEDataFile from POSTED database
            if ((!length(load_other)) || load_database) {
                files <- c(files, TEDataFile$new(private$tid, pathOfTEDFile(private$tid)))
            }

            # load TEDataFiles specified as arguments
            if (length(load_other)) {
                for (o in load_other) {
                    if (is(o, "TEDataFile")) {
                        files <- c(files, o)
                    } else if (is(o, "character")) {
                        files <- c(files, TEDataFile$new(private$tid, o))
                    } else {
                        stop(paste("Unknown load type:", class(o)))
                    }
                }
            }

            # raise exception if no TEDataFiles can be loaded
            if (!length(files)) {
                stop(paste("No TEDataFiles to load for technology", private$tid))
            }

            # load all TEDataFiles and check consistency if requested
            loadedFiles <- list()
            for (f in files) {
                f <- f$load()
                if (check_incons) {
                    f <- check(f)
                }
                loadedFiles <- c(loadedFiles, f)
            }
            files <- loadedFiles

            # compile dataset from the dataframes loaded from the individual files
            private$df <- do.call(rbind, lapply(files, function(f) f$data()))
        # Description
        # Check that the entry type and flow type are valid.
        # Filter out invalid entries.
        },
        checkTypes = function() {
            cond <- private$df$type %in% names(private$tspecs$entry_types) &
                    (private$df$flow_type %in% names(flowTypes) |
                     is.na(private$df$flow_type))
            private$df <- private$df[cond,]
            rownames(private$df) <- NULL
        },
        # Description
        # Set default reference and reported units and normalise.
        adjustUnits = function() {
            # set default reference units for all entry types
            private$setRefUnitsDef()
            # normalise reference units of all entries
            private$normRefUnits()
            # set default reported units for all entry types
            private$setRepUnitsDef()
            # normalise reported units of all entries
            private$normRepUnits()
        },
        # Description
        # Set default reference units for all entry types.
        # Create mapping from default reference dimension to default reference unit where possible.
        # Apply mapping to all entry types.
        # Override with default reference unit if given.
        setRefUnitsDef = function() {
            private$refUnits <- list()
            for (typeid in names(private$tspecs$entry_types)) {
                # set to nan if entry type has no reference dimension
                if (!'ref_dim' %in% names(private$tspecs$entry_types[[typeid]])) {
                    private$refUnits[[typeid]] <- NaN
                } else {
                    # get reference dimension
                    refDim <- private$tspecs$entry_types[[typeid]]$ref_dim
                    
                    # create a mapping from dimensions to default units
                    unitMappings <- defaultUnits
                    if (!is.null(self$refFlow())) {
                        unitMappings <- c(unitMappings, list('[flow]'=flowTypes[[self$refFlow()]]$default_unit))
                    }

                    # map reference dimensions to default reference units
                    private$refUnits[[typeid]] <- refDim
                    for (dim in names(unitMappings)) {
                        private$refUnits[[typeid]] <- gsub(dim, unitMappings[[dim]], private$refUnits[[typeid]], fixed=TRUE)
                    }
                }
            }
            # override with default reference unit of specific technology
            if ('default-ref-units' %in% names(private$tspecs)) {
                private$refUnits[names(private$tspecs[["default-ref-units"]])] <- private$tspecs[["default-ref-units"]]
                #private$refUnits <- c(private$refUnits, private$tspecs[["default-ref-units"]])
            }
        },
        # Description
        # Normalise reference units of all entries.
        # Calculate conversion factor from current reference unit to default reference unit.
        # Apply conversion factor to all entries.
        # Set converted value, uncertainty and unit.
        normRefUnits = function() {
            # default reference value is 1.0
            private$df$reference_value[is.na(private$df$reference_value)] <- 1.0

            # add default reference unit conversion factor
            private$df$reference_unit_default <- apply(private$df, 1, function(row) {return(private$refUnits[[row['type']]]) })
            private$df$reference_unit_factor <- 1.0

            private$df[!is.na(private$df["reference_unit"]), 'reference_unit_factor'] <-
                convUnitDF(private$df[!is.na(private$df["reference_unit"]), ], 'reference_unit', 'reference_unit_default', self$refFlow())

            # set converted value and unit
            private$df <- tibble::add_column(private$df, value=private$df$reported_value / private$df$reference_value / private$df$reference_unit_factor, .after=colnames(private$df)[7])
            private$df <- tibble::add_column(private$df, unc=private$df$reported_unc / private$df$reference_value / private$df$reference_unit_factor, .after='value')
            private$df <- tibble::add_column(private$df, unit=private$df$reported_unit, .after='unc')

            # drop old unit and value columns
            private$df <- private$df[, -grep("^(reported|reference)_(value|unc|unit).*$", colnames(private$df))]
        },
        # Description
        # Set default reported units for all entry types.
        # Create mapping from default reported dimension to default reported unit where possible.
        # Apply mapping to all entry type and assign a tuple of type, flow type and unit
        setRepUnitsDef = function() {
            types <- unique(c(names(private$tspecs$entry_types), 'fopex', 'fopex_spec'))
            private$repUnits <- list()
            for (typeid in types) {
                # get reported dimension of entry type
                repDim <- private$tspecs$entry_types[[typeid]]$rep_dim

                # map reported dimensions to target reported units
                repUnit <- repDim
                for (dim in names(defaultUnits)) {
                    repUnit <- gsub(dim, defaultUnits[[dim]], repUnit, fixed=TRUE)
                }
                if (!'[flow]' %in% repUnit) {
                    private$repUnits <- c(private$repUnits, list(list(type=typeid, flow_type=NaN, unit=repUnit)))
                } else {
                    for (flowid in unique(private$df[private$df$type == typeid, 'flow_type'])) {
                        repUnitFlow <- gsub('\\[flow\\]', flowTypes[[flowid]]$default_unit, repUnit)
                        private$repUnits <- c(private$repUnits, list(list(type=typeid, flow_type=flowid, unit=repUnitFlow)))
                    }
                }
            }
        },
        # Description
        # Normalise reported units of all entries.
        # Calculate conversion factor from current reported unit to default reported unit.
        # This is done by joining with the default reported unit for the type and flow type.
        # Apply conversion factor to all entries.
        # Set converted value, uncertainty and unit.
        normRepUnits = function() {

            dfRepUnitsList <- list()
            for (e in private$repUnits){
                dfRepUnitsList <- c(dfRepUnitsList, list(as.data.frame(e)))
            }
            dfRepUnits <- do.call(rbind, dfRepUnitsList)

            dfRepUnits$unit_convert <- dfRepUnits$unit
            
            performJoinFlowTypeTolerance <- function(row) {
                # define columns to join on
                joinCols <- c('type')
                # add flow_type to join columns if it is specified in dfRepUnits and not NaN
                if (nrow(dfRepUnits[dfRepUnits$type == row[["type"]] & dfRepUnits$flow_type == "NaN", ]) == 0) {
                    joinCols <- c(joinCols, 'flow_type')
                }

                # convert row to dataframe
                row <- t(as.data.frame(row))

                # join row df with dfRepUnits on joinCols and leave out suffixes for row
                joinResult <- merge(row, dfRepUnits, by=joinCols, suffixes=c('', '.y'))
                joinResult <- joinResult[, !grepl('\\.y$', colnames(joinResult))]

                return(joinResult)
            }

            # perform the FlowTypeTolerance join on all rows
            dfJoins <- apply(private$df, 1, performJoinFlowTypeTolerance)
            # concat all the results to one dataframe
            dfJoins <- dfJoins %>% do.call(rbind, .)
            private$df <- as.data.frame(dfJoins)[, c(colnames(private$df), 'unit_convert')]
            convFactor <- convUnitDF(private$df, 'unit', 'unit_convert')

            private$df$value <- as.numeric(private$df$value) * convFactor
            private$df$unc <- as.numeric(private$df$unc) * convFactor
            private$df$unit <- private$df$unit_convert
            private$df <- private$df[, !grepl('unit_convert', colnames(private$df))]
        },
        # Description
        # Convert values to defined units.
        # @param type_units A list of units for entry types that are not of type flow.
        # @param flow_units A list of units for entry types that are of type flow.
        convertUnits = function(type_units = NULL, flow_units = NULL) {
            # raise exception if no updates to units are provided
            if (is.null(type_units) && is.null(flow_units)) {
                return()
            }

            # update reported units of dataset from function argument
            for (record in private$repUnits) {
                if (!is.null(type_units) && record$type %in% names(type_units)) {
                    record$unit <- type_units[[record$type]]
                } else if (!is.null(flow_units) && 'flow_type' %in% record && record$flow_type %in% names(flow_units)) {
                    record$unit <- flow_units[[record$flow_type]]
                }
            }
            # normalise reported units
            private$normRepUnits()
        }
    ),
    public = list( 
        #' @description
        #' Create a TEDataSet object.
        #' @param tid The technology ID.
        #' @param data The data frame.
        #' @param load_other Other data files to load.
        #' @param load_database Whether to load the default data file from the POSTED database.
        #' @param check_incons Whether to check for inconsistencies in the data.
        initialize = function(tid, data = NULL, load_other=list(), load_database=FALSE, check_incons=FALSE) {
            # initialise TEBase fields
            super$initialize(tid)
            # initialise object fields
            private$tid <- tid
            private$load_other <- load_other
            private$load_database <- load_database
            private$check_incons <- check_incons
            if (!is.null(data)) {
                private$df <- data
            } else {
                private$df <- data.frame(NULL)
                # read TEDataFiles and combine into dataset
                private$loadFiles(load_other, load_database, check_incons)
                # check types
                private$checkTypes()
                # adjust units: set default reference and reported units and normalise
                private$adjustUnits()
            }
        },
        #' @description
        #' Get the data frame.
        #' @return The data frame.
        data = function() {
            private$df
        },
        #' @description
        #' Get the reported unit of an entry type.
        #' @param typeid The entry type ID.
        #' @param flowid The flow type ID. NULL if not applicable.
        getRepUnit = function(typeid, flowid = NULL) {
            if (is.null(flowid)) {
                filtered <- private$repUnits[private$repUnits$type == typeid]
                return (filtered[[1]]$unit)
            } else {
                filtered <- private$repUnits[private$repUnits$type == typeid & private$repUnits$flow_type == flowid]
                return(filtered[[1]]$unit)
            }
        },
        #' @description
        #' Get the reference unit of an entry type.
        #' @param typeid The entry type ID.
        #' @param flowid The flow type ID. NULL if not applicable.
        getRefUnit = function(typeid, flowid = NULL) {
            private$refUnits[[typeid]]
        },
        #' @description
        #' Query the data frame
        #' @param ... The query parameters.
        query = function(...) {
            TEDataSet$new(
                tid=private$tid,
                data=subset(private$df, ...),
            )
        }
    )
)
