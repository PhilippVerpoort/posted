function applyPlotlyTheme() {
    const scheme = document.body.getAttribute("data-md-color-scheme");

    const isDark = scheme === "slate";

    const fontColor = isDark ? "#e0e0e0" : "#222222";
    const gridColor = isDark ? "#444444" : "#dddddd";

    document.querySelectorAll(".js-plotly-plot").forEach(plot => {
        Plotly.relayout(plot, {
            "font.color": fontColor,
            "xaxis.gridcolor": gridColor,
            "yaxis.gridcolor": gridColor,
            "xaxis.zerolinecolor": gridColor,
            "yaxis.zerolinecolor": gridColor,
            "xaxis.linecolor": gridColor,
            "yaxis.linecolor": gridColor
        });
    });
}

document.addEventListener("DOMContentLoaded", applyPlotlyTheme);

// Listen for MkDocs theme toggle
document.addEventListener("DOMContentLoaded", () => {
    const observer = new MutationObserver(applyPlotlyTheme);
    observer.observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
});
