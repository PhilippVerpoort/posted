# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: R
#     language: R
#     name: ir
# ---

# + vscode={"languageId": "r"}
devtools::load_all()

# + vscode={"languageId": "r"}
par(bg = "white")
plot(1:10)

# + vscode={"languageId": "r"}
tedf <- TEDF$new("tech/Electrolysis")$load()
tedf$data

# + vscode={"languageId": "r"}
 DataSet$new('Tech|Electrolysis')$normalise(override=list('Tech|Electrolysis|Input Capacity|elec'= 'kW', 'Tech|Electrolysis|Output Capacity|h2'= 'kW;LHV'))  %>% filter(source=='Vartiainen22')

# + vscode={"languageId": "r"}
DataSet$new('Tech|Electrolysis')$normalise(override=list('Tech|Electrolysis|Output Capacity|h2'= 'kW;LHV'))

# + vscode={"languageId": "r"}
DataSet$new('Tech|Electrolysis')$select(period=2020, subtech='AEL', size='100 MW', override=list('Tech|Electrolysis|Output Capacity|h2'= 'kW;LHV'))

# + vscode={"languageId": "r"}
DataSet$new('Tech|Electrolysis')$select(period=2030, source='Yates20', subtech='AEL', size='100 MW', override={'Tech|Electrolysis|Output Capacity|h2'= 'kW;LHV'}, extrapolate_period=FALSE)

# + vscode={"languageId": "r"}
DataSet$new('Tech|Electrolysis')$select(subtech=c('AEL', 'PEM'), size='100 MW', override={'Tech|Electrolysis|Input Capacity|Electricity'= 'kW'})

# + vscode={"languageId": "r"}
DataSet$new('Tech|Electrolysis')$aggregate(subtech='AEL', size='100 MW', agg='subtech', override={'Tech|Electrolysis|Output Capacity|Hydrogen'='kW;LHV'})

# + vscode={"languageId": "r"}
# DataSet$new('Tech|Methane Reforming')$aggregate(period=2030).query("variable.str.contains('OM Cost')"))
# display(DataSet('Tech|Methane Reforming').aggregate(period=2030).query("variable.str.contains('Demand')"))
DataSet$new('Tech|Methane Reforming')$aggregate(period=2030) %>% arrange(variable)

# + vscode={"languageId": "r"}
DataSet$new('Tech|Direct Air Capture')$normalise()

# + vscode={"languageId": "r"}
DataSet$new('Tech|Direct Air Capture')$select()

# + vscode={"languageId": "r"}
TEDF$new('Tech|Haber-Bosch with ASU')$load()# $check()
DataSet$new('Tech|Haber-Bosch with ASU')$normalise()

# + vscode={"languageId": "r"}
DataSet$new('Tech|Haber-Bosch with ASU')$select(period=2020)

# + vscode={"languageId": "r"}
DataSet$new('Tech|Haber-Bosch with ASU')$aggregate(period=2020)

# + vscode={"languageId": "r"}

