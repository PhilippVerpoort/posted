from .columns import (
    AbstractColumnDefinition,
    VariableDefinition,
    ValueDefinition,
    UnitDefinition,
    CommentDefinition,
)
from .fields import (
    AbstractFieldDefinition,
    CustomFieldDefinition,
    PeriodFieldDefinition,
    SourceFieldDefinition,
)


predefined_columns = {
    "period": PeriodFieldDefinition(
        name="Period",
        description="The period that this value is reported for.",
    ),
}

def base_column_src():
    return SourceFieldDefinition(
        name="Source",
        description="A reference to the source that this entry was taken "
                    "from.",
    )

base_columns_src_detail = {
    "source_detail": CommentDefinition(
        name="Source Detail",
        description="Detailed information on where in the source this entry "
        "can be found.",
        required=True,
    ),
}

base_columns_other = {
    "variable": VariableDefinition(
        name="Variable",
        description="The reported variable.",
        required=True,
    ),
    "reference_variable": VariableDefinition(
        name="Reference Variable",
        description="The reference variable. This is used as an addition to "
        "the reported variable for clear, simplified, and "
        "transparent data reporting.",
        required=False,
    ),
    "value": ValueDefinition(
        name="Value",
        description="The reported value.",
        required=True,
    ),
    "uncertainty": ValueDefinition(
        name="Uncertainty",
        description="The reported uncertainty.",
        required=False,
    ),
    "unit": UnitDefinition(
        name="Unit",
        description="The reported unit that goes with the reported value.",
        required=True,
    ),
    "reference_value": ValueDefinition(
        name="Reference Value",
        description="The reference value. This is used as an addition to the "
        "reported variable for clear, simplified, and transparent "
        "data reporting.",
        required=False,
    ),
    "reference_unit": UnitDefinition(
        name="Reference Unit",
        description="The reference unit. This is used as an addition to the "
        "reported variable to clear, simplified, and transparent "
        "data reporting.",
        required=False,
    ),
    "comment": CommentDefinition(
        name="Comment",
        description="A generic free text field commenting on this entry.",
        required=False,
    ),
}

base_columns = (
    ["source"]
    + list(base_columns_src_detail)
    + list(base_columns_other)
)


def read_fields_comments(
    columns: dict,
) -> (
    dict[str, AbstractFieldDefinition],
    dict[str, CommentDefinition],
):
    """
    Read the fields of a variable.

    Parameters
    ----------
        columns: dict
            Dictionary defining the fields and comments

    Returns
    -------
        fields
            Dictionary containing the fields
        comments
            Dictionary containing the comments
    """
    fields: dict[str, AbstractFieldDefinition] = {}
    comments: dict[str, CommentDefinition] = {}

    for col_id, col_specs in columns.items():
        if isinstance(col_specs, str):
            fields[col_id] = predefined_columns[col_specs]
        elif col_specs["type"] in ("case", "component"):
            fields[col_id] = CustomFieldDefinition(**col_specs)
        elif col_specs["type"] == "comment":
            comments[col_id] = CommentDefinition(
                **{k: v for k, v in col_specs.items() if k != "type"},
                required=False,
            )
        else:
            raise Exception(f"Unknown field type: {col_id}")

    # Make sure the field ID is not the same as for a base column.
    for col_id in fields:
        if col_id in base_columns:
            raise Exception(
                f"Field ID cannot be equal to a base column ID: {col_id}"
            )

    return fields, comments
