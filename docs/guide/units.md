---
title: Units
---

# Units

POSTED does not implement its own unit system. It relies on [`cet-units`](https://philippverpoort.github.io/cet-units/latest/), a unit registry for climate, energy, and technology applications that extends the [`pint`](https://pint.readthedocs.io/) library. Every unit string in a TEDF must be understood by this registry. This page summarises the parts of the notation that matter for POSTED. The full documentation is available on the `cet-units` website.

## Plain units

Standard physical units and SI prefixes are available as in `pint`, e.g. `kW`, `MWh`, `GJ`, `t`, `kg`, `hour`, `day`. Compound units use `/` and `*`, e.g. `t/year` or `kg_H2/day`.

The units `a`, `year`, and `yr` are synonyms. For convenience, one year is defined as 365 days in `cet-units`. Capacities given per year and per hour can therefore be converted exactly.

Percentages are written as `percent` or `pct` and are dimensionless. A value of 90 with unit `percent` is converted to 0.9 when the target unit is `dimensionless`.

## Flow units

Flows such as hydrogen, ammonia, or natural gas can be quantified by mass, volume, or energy content. `cet-units` provides flow-specific units that encode the substance as a suffix, which allows conversion between these dimensions.

| Notation | Meaning | Example |
|---|---|---|
| `kg_H2`, `t_NH3` | Mass of the flow | `kg_H2` |
| `cubic_meter_H2_norm` | Volume of the flow at normal conditions | `cubic_meter_NG_norm` |
| `MWh_H2_LHV`, `GJ_NG_HHV` | Energy content based on lower (LHV) or higher (HHV) heating value | `kWh_MeOH_LHV` |
| `kW_NH3_LHV` | Energy flow rate based on heating value | `kW_MeOH_LHV` |

A quantity of `1 kg_H2` can be converted to `MWh_H2_LHV`, and a hydrogen capacity of `1 kg_H2/day` to `kW_H2_LHV`. Conversion between different flows is not possible.

The flows available by default in `cet-units` can be extended. POSTED registers the following additional flow identifiers when it is imported: `crude_oil`, `coal`, `CH4`, `H2`, `H2O`, `MeOH`, `NG`, `NH3`, `O2`.

Where a TEDF column refers to a flow without a flow-specific unit, e.g. `MWh` for electricity or `t` for cement, the plain unit is used. In that case, conversion between dimensions is not available and all sources must report the quantity in the same dimension.

## Currencies

Currencies are written with a base year, e.g. `EUR_2020` or `USD_2023`. `cet-units` converts between base years by deflation and between currencies by exchange rate. Prefixes are permitted, e.g. `MEUR_2018` or `kUSD_2022`. A currency without a year is not a valid unit in POSTED.

Costs that recur annually use a time unit in the denominator, e.g. `EUR_2020/year` for fixed OPEX. Investment costs do not, e.g. `EUR_2020` for CAPEX.

## Default units and overrides

The normalisation step of NO-SL-AG assigns one target unit to each variable in the following way.

1. All units found for the variable are collected, both from the `unit` column where the variable is reported and from the `reference_unit` column where it serves as a reference.
2. Currency units are rewritten to the default currency given by `posted.defaults["currency"]`, which is `EUR_2024` unless changed.
3. The most frequent unit among the rewritten units is chosen as the target unit.
4. Entries in the `units` argument of `normalise()`, `select()`, or `aggregate()` override the automatic choice for the given variables.

The `units` argument maps variable names, without the parent variable, to unit strings.

```python
tedf.aggregate(
    units={
        "CAPEX": "EUR_2024",
        "Output Capacity|Hydrogen": "kW_H2_LHV",
        "Input|Electricity": "MWh",
    }
)
```

Because the automatic choice follows the data, the output units can change when new data is added to a TEDF. Analyses that depend on specific units should set them explicitly.

Variable mappings may introduce variables that are not present in the raw data, e.g. `OPEX Fixed` derived from `OPEX Fixed Relative`. Their units are derived from the units of the variables they are computed from. They can also be set through the `units` argument.

## Dimension checks

The metadata of variable definitions in the database records a dimension and a default unit for each variable, e.g. `[currency]` for CAPEX or `[time]` for lifetime. These entries document the expected dimensionality of a variable. At present, the framework does not check reported units against them. The validation step only checks that each unit string is known to the unit registry.
