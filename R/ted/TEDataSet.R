library(dplyr)
library(magrittr)
library(tibble)

source("R/config/read_config.R")
source("R/path.R")
source("R/ted/TEDataFile.R")
source("R/units/units.R")

TEDataSet <- R6Class("TEDataSet",
    inherit = TEBase,
    private = list(
        tid = NULL,
        load_other = NULL,
        load_database = NULL,
        check_incons = NULL,
        df = NULL,
        refUnits = NULL,
        repUnits = NULL,
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
        },
        checkTypes = function() {
            cond <- private$df$type %in% names(private$tspecs$entry_types) &
                    (private$df$flow_type %in% names(flowTypes) |
                     is.na(private$df$flow_type))
            private$df <- private$df[cond,]
            rownames(private$df) <- NULL
        },
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
        normRefUnits = function() {
            # default reference value is 1.0
            private$df$reference_value[is.na(private$df$reference_value)] <- 1.0

            # add default reference unit conversion factor
            private$df$reference_unit_default <- apply(private$df, 1, function(row) {return(private$refUnits[[row['type']]]) })
            private$df$reference_unit_factor <- 1.0

            private$df[!is.na(private$df["reference_unit"]), 'reference_unit_factor'] <-
                convUnitDF(private$df[!is.na(private$df["reference_unit"]), ], 'reference_unit', 'reference_unit_default', self$refFlow())

            # set converted value and unit
            private$df <- add_column(private$df, value=private$df$reported_value / private$df$reference_value / private$df$reference_unit_factor, .after=colnames(private$df)[7])
            private$df <- add_column(private$df, unc=private$df$reported_unc / private$df$reference_value / private$df$reference_unit_factor, .after='value')
            private$df <- add_column(private$df, unit=private$df$reported_unit, .after='unc')

            # drop old unit and value columns
            private$df <- private$df[, -grep("^(reported|reference)_(value|unc|unit).*$", colnames(private$df))]
        },
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
        data = function() {
            private$df
        },
        # get reported unit for entry type
        getRepUnit = function(typeid, flowid = NULL) {
            if (is.null(flowid)) {
                filtered <- private$repUnits[private$repUnits$type == typeid]
                return (filtered[[1]]$unit)
            } else {
                filtered <- private$repUnits[private$repUnits$type == typeid & private$repUnits$flow_type == flowid]
                return(filtered[[1]]$unit)
            }
        },
        # get reference unit for entry type
        getRefUnit = function(typeid, flowid = NULL) {
            private$refUnits[[typeid]]
        },
        query = function(...) {
            TEDataSet$new(
                tid=private$tid,
                data=subset(private$df, ...),
            )
        }
    )
)