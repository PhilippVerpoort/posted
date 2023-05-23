library(dplyr)
library(magrittr)
library(tibble)

source("src/R/config/read_config.R")
source("src/R/path.R")
source("src/R/units/units.R")


TEDataSet <- function(tid, load_other=list(), load_database=FALSE, to_default_units=TRUE) {
    # read TEDataFiles and combine into dataset
    df <- TEDataSet.loadFiles(tid=tid, load_other=load_other, load_database=load_database)

    # set default reference units for all entry types
    refUnitsDef <- TEDataSet.setRefUnitsDef(tid=tid)

    # normalise all entries to a unified reference
    df <- TEDataSet.normToRef(tid=tid, dataset=df, refUnitsDef=refUnitsDef)

    # create TEDataSet list object
    obj <- list(
      tid=tid,
      refUnitsDef=refUnitsDef,
      data=df
    )

    # convert values to default units
    if (to_default_units) {
        obj <- TEDataSet.convertUnits(obj)
    }

    # return TEDataSet object as list
    return(obj)
}


# load TEDatFiles and compile into dataset
TEDataSet.loadFiles <- function(tid, load_other, load_database) {
    files <- list()

    # load default TEDataFile from POSTED database
    if ((!length(load_other)) || load_database) {
        files[[length(files)+1]] <- TEDataFile.read(tid, pathOfTEDFile(tid))
    }

    # load TEDataFiles specified as arguments
    if (!!length(load_other)) {
        for (o in load_other) {
            if (typeof(o) == "list") {
                files[[length(files)+1]] <- o
            }
            else if (typeof(o) == "character") {
                files[[length(files)+1]] <- TEDataFile.read(tid, o)
            }
            else {
                stop("Unknown load type.")
            }
        }
    }

    # raise exception if no TEDataFiles can be loaded
    if (!length(files)) {
        stop(paste0("No TEDataFiles to load for technology '", tid, "'."))
    }

    # compile dataset from the dataframes loaded from the individual files
    datasetList <- list()
    for (i in seq_along(files)) {
        datasetList[[i]] <- files[[i]]$data
    }
    dataset <- dplyr::bind_rows(datasetList)

    # return
    return(dataset)
}


# determine default reference units of entry types from technology class
TEDataSet.setRefUnitsDef <- function(tid) {
    tspecs <- techs[[tid]]

    refUnitsDef <- list()
    for (typeid in names(tspecs$entry_types)) {
        # get reference dimension
        refDim <- tspecs$entry_types[[typeid]]$ref_dim

        # create a mapping from dimensions to default units
        unitMappings <- defaultUnits
        if ('reference_flow' %in% names(tspecs)) {
            a <- list(flow=flowTypes[[tspecs$reference_flow]]$default_unit)
            unitMappings <- append(unitMappings, a)
        }

        # map reference dimensions to default reference units
        refUnitsDef[[typeid]] <- refDim
        for (dim in names(unitMappings)) {
            unit <- unitMappings[[dim]]
            refUnitsDef[[typeid]] <- sub(dim, unit, refUnitsDef[[typeid]])
        }
    }

    # override with default reference unit of specific technology
    if ('default-ref-units' %in% names(tspecs)) {
        for (dim in names(tspecs[['default-ref-units']])) {
            refUnitsDef[[dim]] <- tspecs[['default-ref-units']][[dim]]
        }
    }

    # return
    return(refUnitsDef)
}


# apply references to values and units
TEDataSet.normToRef <- function(tid, dataset, refUnitsDef) {
    # default reference value is 1.0
    dataset$reference_value[is.na(dataset["reference_value"])] <- 1.0

    # add default reference unit conversion factor
    dataset$reference_unit_default <- apply(dataset, 1, function(row) {return(refUnitsDef[[row['type']]]) })
    dataset$reference_unit_factor <- 1.0
    dataset[!is.na(dataset["reference_unit"]), 'reference_unit_factor'] <-
        convUnitDF(dataset[!is.na(dataset["reference_unit"]), ], 'reference_unit', 'reference_unit_default', techs[[tid]]$reference_flow)

    # set converted value and unit
    dataset <- add_column(dataset, value=dataset$reported_value / dataset$reference_value / dataset$reference_unit_factor, .after='period')
    dataset <- add_column(dataset, unc=dataset$reported_unc / dataset$reference_value / dataset$reference_unit_factor, .after='value')
    dataset <- add_column(dataset, unit=dataset$reported_unit, .after='unc')

    # drop columns by
    dataset <- dataset[, -grep("^(reported|reference)_(value|unc|unit).*$", colnames(dataset))]

    # return
    return(dataset)
}


# convert values to defined units (use defaults if non provided)
TEDataSet.convertUnits <- function(self, type_units = NULL, flow_units = NULL) {
    # get object fields
    tid <- self$tid
    tspecs <- techs[[tid]]
    df <- self$data
    refUnitsDef <- self$refUnitsDef

    # set empty list if arguments are NULL
    if(is.null(type_units)) {
        type_units <- list()
    }
    if(is.null(flow_units)) {
        flow_units <- list()
    }

    # set reported units to convert to
    repUnitsTarget <- list()
    for (typeid in unique(df$type)) {
        # get reported dimension of entry type
        repDim <- tspecs$entry_types[[typeid]]$rep_dim

        # map reported dimensions to target reported units
        repUnit <- repDim
        for (dim in names(defaultUnits)) {
            unit <- defaultUnits[[dim]]
            repUnit <- sub(dim, unit, repUnit)
        }
        if (!grepl('flow', repUnit, fixed=TRUE)) {
            repUnitsTarget[[length(repUnitsTarget)+1]] <- list(type=typeid, flow_type=NA, 'unit_convert'=repUnit)
        } else {
            for (flowid in unique(filter(df, type==typeid)$flow_type)) {
                repUnitFlow <- sub('flow', flowTypes[[flowid]]$default_unit, repUnit)
                repUnitsTarget[[length(repUnitsTarget)+1]] <- list(type=typeid, flow_type=flowid, 'unit_convert'=repUnitFlow)
            }
        }
    }

    # override from function argument
    for (record in repUnitsTarget) {
        if (record$type %in% names(type_units)) {
            record$unit_convert <- type_units[[record$type]]
        } else if (('flow_type' %in% names(record)) && (record$flow_type %in% names(flow_units))) {
            record$unit_convert <- flow_units[[record$flow_type]]
        }
    }

    # add reported unit conversion factor
    df <- merge(df,
        as.data.frame(do.call(bind_rows, repUnitsTarget)),
        by=c('type', 'flow_type')
    )
    convFactor <- convUnitDF(df, 'unit', 'unit_convert')
    df[, 'value'] <- convFactor * df[, 'value']
    df[, 'unc'] <- convFactor & df[, 'unc']
    df[, 'unit'] <- df[, 'unit_convert']
    df <- df %>% select(-unit_convert)

    # return TEDataSet object as list
    return(list(
      tid=tid,
      refUnitsDef=refUnitsDef,
      data=df
    ))
}


TEDataSet.generateTable <- function (self,
    q_periods,
    q_subtech=NULL,
    q_mode=NULL,
    q_src_ref=NULL,
    masks_database=TRUE,
    masks_other=NULL,
    no_agg=NULL
) {
    # get object fields
    self._tid <- self$tid
    self._tspecs <- techs[[self._tid]]
    self._df <- self$data
    self._refUnitsDef <- self$refUnitsDef

    # the dataset it the starting-point for the table
    table <- self._df

    # drop columns that are not considered
    table <- table %>% select(-c('region', 'unc', 'unit', 'comment', 'src_comment'))

    # insert missing periods
    table <- TEDataSet.insertMissingPeriods(table)

    # apply quick fixes
    table <- TEDataSet.quickFixes(table)

    # query by selected sources
    if(is.null(q_src_ref)) {
        # pass
    } else if (!is.vector(q_src_ref) && (typeof(q_src_ref) == "character")) {
        table <- table %>% filter(src_ref==q_src_ref)
    } else if ((typeof(src_ref) == "list") || (is.vector(q_src_ref) && (typeof(q_src_ref) == "character"))) {
        table <- table %>% filter(src_ref %in% q_src_ref)
    }

    # expand technology specifications for all subtechs and modes
    expandCols <- list()
    loopList <- list(subtech=q_subtech, mode=q_mode)
    for (colID in names(loopList)) {
        selectArg <- loopList[[colID]]
        colIDs <- paste0(colID, 's')
        if (is.null(selectArg) && (colIDs %in% names(self._tspecs)) && !is.null(self._tspecs[[colIDs]])) {
            expandCols[[colID]] <- self._tspecs[[colIDs]]
        } else if (!is.vector(selectArg) && (typeof(selectArg) == "character")) {
            expandCols[[colID]] <- list(selectArg)
        } else if ((typeof(selectArg) == "list") || (is.vector(selectArg) && (typeof(selectArg) == "character"))) {
            expandCols[[colID]] <- selectArg
        }
    }
    table <- TEDataSet.expandTechs(table, expandCols)

    # group by identifying columns and select periods/generate time series
    if (!is.vector(q_periods) || typeof(q_periods) == "list") {
        q_periods <- list(q_periods)
    }
    table <- TEDataSet.selectPeriods(table, q_periods)

    # return
    return(table)
}


# insert missing periods
TEDataSet.insertMissingPeriods <- function(table) {
    # TODO: insert year of publication instead of current year
    table[is.na(table["period"]), "period"] <- 2023

    # return
    return(table)
}


# quick fix function for types not implemented yet
TEDataSet.quickFixes <- function(table) {
    # drop types that are not implemented (yet): flh, lifetime, efficiency, etc
    # TODO: implement those types so we don't need to remove them
    dropTypes <- c("flh", "lifetime", "energy_eff")
    table <- table %>% filter(!type %in% dropTypes)

    # return
    return(table)
}


# expand based on subtechs and modes
TEDataSet.expandTechs <- function (table, expandCols) {
    dfMerge <- as.data.frame(do.call(cbind, expandCols))

    # loop over affected columns (subtech and mode)
    for (colID in names(expandCols)) {
        table <- rbind(
            table[!is.na(table[[colID]]),],
            table[is.na(table[[colID]]),] %>% select(-all_of(colID)) %>% merge(as.data.frame(select(dfMerge, all_of(colID))))
        )
    }

    # return
    return(table)
}


# group by identifying columns and select periods/generate time series
TEDataSet.selectPeriods <- function (table, q_periods) {
    return(table)
}
