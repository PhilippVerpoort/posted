from ..noslag import TEDF


try:
    from ipywidgets import Button, HBox, VBox, Output
    from ipydatagrid import DataGrid, Expr, TextRenderer
except ModuleNotFoundError:
    raise Exception("The `ipydatagrid` package must be installed for this "
                    "feature to work.")


def build_edit_grid(tedf: TEDF):
    # Create DataGrid.
    grid = DataGrid(
        tedf.raw,
        editable=True,
        auto_fit_columns=True,
    )
    grid.auto_fit_columns = True

    # For printing messages to the user.
    output = Output()

    # Define function for clearing cell inputs (for columns containing floats).
    def save_to_file(b):
        tedf.save_to_file()
        with output:
            print("Saved.")

    # Add buttons.
    button_add = Button(description="Insert below selected rows")
    button_del = Button(description="Delete selected rows")
    button_save = Button(description="Save to file")
    button_save.on_click(save_to_file)

    return VBox([grid, HBox([button_add, button_del, button_save, output])])
