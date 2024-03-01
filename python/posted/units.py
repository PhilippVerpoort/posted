import numpy as np
import pandas as pd
import iam_units

from posted.path import databases
from posted.config import flows


# set up pint unit registry: use iam_units as a basis, load custom definitions, add pint_pandas, set display format,
ureg = iam_units.registry
for database_path in databases.values():
    units_definitions = database_path / 'unit_definitions.txt'
    if units_definitions.exists():
        ureg.load_definitions(units_definitions)
iam_units.currency.configure_currency("EXC", "2005")
ureg.Unit.default_format = "~P"


# define unit variants
unit_variants = {
    'LHV': {'param': 'energycontent', 'value': 'energycontent_LHV', 'dimension': 'energy', },
    'HHV': {'param': 'energycontent', 'value': 'energycontent_HHV', 'dimension': 'energy', },
    'norm': {'param': 'density', 'value': 'density_norm', 'dimension': 'volume', },
    'std': {'param': 'density', 'value': 'density_std', 'dimension': 'volume', },
}


# check if unit is allowed for variable
def unit_allowed(unit: str, flow_id: None | str, dimension: str):
    if not isinstance(unit, str):
        raise Exception('Unit to check must be string.')

    # split unit into pure unit and variant
    try:
        unit, variant = split_off_variant(unit)
    except:
        return False, f"Inconsistent unit variant format in '{unit}'."

    try:
        unit_registered = ureg(unit)
    except:
        return False, f"Unknown unit '{unit}'."

    if flow_id is None:
        if '[flow]' in dimension:
            return False, f"No flow_id provided even though [flow] is in dimension."
        if variant is not None:
            return False, f"Unexpected unit variant '{variant}' for dimension [{dimension}]."
        if (dimension == 'dimensionless' and unit_registered.dimensionless) or unit_registered.check(dimension):
            return True, ''
        else:
            return False, f"Unit '{unit}' does not match expected dimension [{dimension}]."
    else:
        if '[flow]' not in dimension:
            if (dimension == 'dimensionless' and unit_registered.dimensionless) or unit_registered.check(dimension):
                return True, ''
        else:
            check_dimensions = [
                (dimension.replace(
                    '[flow]', f"[{dimension_base}]"), dimension_base, base_unit)
                for dimension_base, base_unit in [('mass', 'kg'), ('energy', 'kWh'), ('volume', 'm**3')]
            ]
            for check_dimension, check_dimension_base, check_base_unit in check_dimensions:
                if unit_registered.check(check_dimension):
                    if variant is None:
                        if any(
                            (check_dimension_base == variant_specs['dimension']) and
                            flows[flow_id][variant_specs['value']] is not np.nan
                            for variant, variant_specs in unit_variants.items()
                        ):
                            return False, (f"Missing unit variant for dimension [{check_dimension_base}] for unit "
                                           f"'{unit}'.")
                    elif unit_variants[variant]['dimension'] != check_dimension_base:
                        return False, f"Variant '{variant}' incompatible with unit '{unit}'."

                    default_unit, default_variant = split_off_variant(
                        flows[flow_id]['default_unit'])
                    ctx_kwargs = ctx_kwargs_for_variants(
                        [variant, default_variant], flow_id)

                    if ureg(check_base_unit).is_compatible_with(default_unit, 'flocon', **ctx_kwargs):
                        return True, ''
                    else:
                        return False, f"Unit '{unit}' not compatible with flow '{flow_id}'."

        return False, f"Unit '{unit}' is not compatible with dimension [{dimension}]."


# get conversion factor between units, e.g. unit_from = "MWh;LHV" and unit_to = "m**3;norm"
def unit_convert(unit_from: str | float, unit_to: str | float, flow_id: None | str = None) -> float:
    # return nan if unit_from or unit_to is nan
    if unit_from is np.nan or unit_to is np.nan:
        return np.nan

    # skip flow conversion if no flow_id specified
    if flow_id is None or pd.isna(flow_id):
        return ureg(unit_from).to(unit_to).magnitude

    # get variants from units
    pure_units = []
    variants = []
    for u in (unit_from, unit_to):
        pure_unit, variant = split_off_variant(u)
        pure_units.append(pure_unit)
        variants.append(variant)

    unit_from, unit_to = pure_units

    # if no variants a specified, we may proceed without a flow context
    if not any(variants):
        return ureg(unit_from).to(unit_to).magnitude

    # if both variants refer to the same dimension, we need to manually calculate the conversion factor and proceed
    # without a flow context
    if len(variants) == 2:
        variant_params = {
            unit_variants[v]['param'] if v is not None else None
            for v in variants
        }
        if len(variant_params) == 1:
            param = next(iter(variant_params))
            value_from, value_to = (
                flows[flow_id][unit_variants[v]['value']] for v in variants)

            conv_factor = (ureg(value_from) / ureg(value_to)
                           if param == 'energycontent' else
                           ureg(value_to) / ureg(value_from))

            return conv_factor.magnitude * ureg(unit_from).to(unit_to).magnitude

    # perform the actual conversion step with all required variants
    ctx_kwargs = ctx_kwargs_for_variants(variants, flow_id)
    return ureg(unit_from).to(unit_to, 'flocon', **ctx_kwargs).magnitude


# get key-word arguments for unit conversion for context from flow specs
def ctx_kwargs_for_variants(variants: list[str | None], flow_id: str):
    # set default conversion parameters to NaN, such that conversion fails with a meaningful error message in their
    # absence. when this is left out, the conversion fails will throw a division-by-zero error message.
    ctx_kwargs = {'energycontent': np.nan, 'density': np.nan}
    ctx_kwargs |= {
        unit_variants[v]['param']: flows[flow_id][unit_variants[v]['value']]
        for v in variants if v is not None
    }
    return ctx_kwargs


# split unit into pure unit and variant, e.g. MWh;LHV into MWh and LHV
def split_off_variant(unit: str):
    tokens = unit.split(';')
    if len(tokens) == 1:
        pure_unit = unit
        variant = None
    elif len(tokens) > 2:
        raise Exception(f"Too many semi-colons in unit '{unit}'.")
    else:
        pure_unit, variant = tokens
    if variant is not None and variant not in unit_variants:
        raise Exception(f"Cannot find unit variant '{variant}'.")
    return pure_unit, variant
