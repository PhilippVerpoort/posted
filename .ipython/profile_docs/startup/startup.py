import os


import plotly.io as pio
from itables import show, init_notebook_mode


# Set up plotly.
pio.renderers.default = "notebook_connected"
pio.templates["docs_template"] = (
    pio.templates["simple_white"]
    .update(layout=dict(
        dragmode=False,
        xaxis_fixedrange=True,
        yaxis_fixedrange=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    ))
)
pio.templates.default = "docs_template"


# Set up itables.
init_notebook_mode(connected=True)


# Override TEDF raw edit with raw output when executing for mkdocs.
IS_DOCS: bool = os.getenv("BUILD_POSTED_DOCS") == "1"
def edit(tedf: "TEDF"):
    if IS_DOCS:
        show(tedf.raw)
    else:
        return tedf.edit_data()


# Silence POSTED warnings when executing for mkdocs.
if IS_DOCS:
    from warnings import filterwarnings
    from posted import POSTEDWarning
    filterwarnings("ignore", category=POSTEDWarning)


# Generate Markdown link to TEDF in public database from variable name.
def link_public_github(var: str):
    var_path = var.replace("|", "/")
    file_path = f"posted/database/tedfs/{var_path}.csv"
    url = "https://github.com/PhilippVerpoort/posted/blob/main/" + file_path
    # return f"[{file_path}]({url})"
    return f"<a href=\"{url}\">{file_path}</a>"
