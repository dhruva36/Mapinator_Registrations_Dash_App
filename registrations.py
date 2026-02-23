from dash import Dash, html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from flask import Flask

# ==========================================================================
# Constants
# ==========================================================================

API_URL = "https://support.econjobmarket.org/api/registrations"
CUTOFF_DATE = "2021-06-01"
ACADEMIC_YEAR_START_MONTH = 6

ACADEMIC_MONTH_LABELS = [
    "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "Jan", "Feb", "Mar", "Apr", "May",
]
ACADEMIC_MONTH_DAYS = [0, 30, 61, 92, 122, 153, 183, 214, 245, 273, 304, 334]

TRACE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]

SIDEBAR_WIDTH = "18rem"

# Maps the date field radio button value to the corresponding year column
# and display label. Used throughout callbacks to avoid branching on
# enrolldate vs date_last_login everywhere.
DATE_FIELDS = {
    "enrolldate": {"year_col": "academic_year", "label": "Enrollment Date"},
    "date_last_login": {"year_col": "login_academic_year", "label": "Last Login Date"},
}

# ==========================================================================
# Data
# ==========================================================================

def get_academic_year(date):
    """Map a calendar date to its academic year (Jun-May cycle)."""
    if date.month >= ACADEMIC_YEAR_START_MONTH:
        return date.year
    return date.year - 1


def date_to_academic_days(date, academic_year):
    """Days elapsed since June 1 of the given academic year."""
    start = pd.Timestamp(year=int(academic_year), month=ACADEMIC_YEAR_START_MONTH, day=1)
    return (date - start).days


def unique_sorted(series):
    """Sorted unique non-null values from a pandas Series."""
    return sorted(x for x in series.unique() if x is not None and not pd.isna(x))


def load_data():
    r = requests.get(API_URL)
    df = pd.DataFrame(r.json())

    df["enrolldate"] = pd.to_datetime(df["enrolldate"])
    df["date_last_login"] = pd.to_datetime(df["date_last_login"])

    cutoff = pd.to_datetime(CUTOFF_DATE)
    df = df[(df["enrolldate"] >= cutoff) & (df["date_last_login"] >= cutoff)]

    df["academic_year"] = df["enrolldate"].apply(get_academic_year)
    df["login_academic_year"] = df["date_last_login"].apply(get_academic_year)

    return df


registration_data = load_data()
total_registrations = len(registration_data)

primary_fields = unique_sorted(registration_data["primary_field"])
countries = unique_sorted(registration_data["country"])
tiers = unique_sorted(registration_data["tier"])
degree_types = unique_sorted(registration_data["degreetype"])
academic_years = unique_sorted(registration_data["academic_year"])
login_academic_years = unique_sorted(registration_data["login_academic_year"])

# ==========================================================================
# Filtering and graph helpers
# ==========================================================================

def filter_data(data, selected_years, selected_degrees, selected_fields,
                selected_countries, selected_tiers, date_field):
    df = data.copy()
    year_col = DATE_FIELDS[date_field]["year_col"]

    for values, col in [
        (selected_years, year_col),
        (selected_degrees, "degreetype"),
        (selected_fields, "primary_field"),
        (selected_countries, "country"),
        (selected_tiers, "tier"),
    ]:
        if values:
            df = df[df[col].isin(values)]

    return df


def build_traces(df, date_field, year_col, years_to_show):
    """Build one Scatter trace per academic year showing cumulative registrations."""
    traces = []
    for i, year in enumerate(years_to_show):
        year_df = df[df[year_col] == year].copy()
        if year_df.empty:
            continue

        year_df = year_df.sort_values(date_field).reset_index(drop=True)
        year_df["cumcount"] = np.arange(1, len(year_df) + 1)

        timeline = [date_to_academic_days(row[date_field], year)
                     for _, row in year_df.iterrows()]

        traces.append(go.Scatter(
            x=timeline,
            y=year_df["cumcount"],
            name=f"{int(year)}-{int(year)+1}",
            mode="lines+markers",
            marker=dict(size=4),
            line=dict(width=2, color=TRACE_COLORS[i % len(TRACE_COLORS)]),
        ))

    return traces


def make_title(label, selected_years):
    base = f"Cumulative Count by {label}"
    if not selected_years:
        return f"{base} - All Years"
    if len(selected_years) == 1:
        y = selected_years[0]
        return f"{base} - {int(y)}-{int(y)+1}"
    return f"{base} - Selected Years"


def academic_xaxis():
    return dict(
        tickmode="array",
        tickvals=ACADEMIC_MONTH_DAYS,
        ticktext=ACADEMIC_MONTH_LABELS,
        showgrid=True,
        gridcolor="lightgray",
        range=[0, 365],
    )

# ==========================================================================
# Layout
# ==========================================================================

SIDEBAR_STYLE = {
    "position": "fixed", "top": 0, "left": 0, "bottom": 0,
    "width": SIDEBAR_WIDTH, "padding": "2rem 1rem",
    "background-color": "#f8f9fa", "border-right": "1px solid #dee2e6",
    "overflow-y": "auto",
}

CONTENT_STYLE = {
    "margin-left": SIDEBAR_WIDTH, "margin-right": "2rem",
    "padding": "2rem 1rem", "padding-bottom": "4rem",
}

FOOTER_STYLE = {
    "position": "fixed", "left": SIDEBAR_WIDTH, "right": 0, "bottom": 0,
    "height": "3rem", "background-color": "#f8f9fa",
    "border-top": "1px solid #dee2e6", "padding": "0.5rem 2rem",
    "display": "flex", "align-items": "center", "justify-content": "center",
}

load_figure_template("LUX")
app_server = Flask(__name__)
app = Dash(__name__, server=app_server, external_stylesheets=[dbc.themes.LUX])

sidebar = html.Div([
    html.H4("FILTERS", className="text-primary mb-4"),
    html.P("Select Characteristics", className="text-muted small mb-4"),
    html.Hr(),

    html.Div([
        html.Label("View by", className="form-label fw-bold mb-2"),
        dcc.RadioItems(
            id="date-field-selector",
            options=[
                {"label": " Enrollment Date", "value": "enrolldate"},
                {"label": " Last Login Date", "value": "date_last_login"},
            ],
            value="enrolldate",
            className="mb-3",
            labelStyle={"display": "block", "margin-bottom": "5px"},
        ),
    ]),
    html.Hr(),

    html.Div([
        html.Label("Academic Year", className="form-label fw-bold mb-2"),
        dcc.Dropdown(id="year-dropdown", options=[], value=[], multi=True,
                     placeholder="Select academic years...", className="mb-3"),
    ]),
    html.Div([
        html.Label("Degree Type", className="form-label fw-bold mb-2"),
        dcc.Dropdown(id="degreetype-dropdown",
                     options=[{"label": d, "value": d} for d in degree_types],
                     value=[], multi=True, placeholder="Select degree types...",
                     className="mb-3"),
    ]),
    html.Div([
        html.Label("Primary Field", className="form-label fw-bold mb-2"),
        dcc.Dropdown(id="primary-field-dropdown",
                     options=[{"label": f, "value": f} for f in primary_fields],
                     value=[], multi=True, placeholder="Select fields...",
                     className="mb-3"),
    ]),
    html.Div([
        html.Label("Country", className="form-label fw-bold mb-2"),
        dcc.Dropdown(id="country-dropdown",
                     options=[{"label": c, "value": c} for c in countries],
                     value=[], multi=True, placeholder="Select countries...",
                     className="mb-3"),
    ]),
    html.Div([
        html.Label("University Tier", className="form-label fw-bold mb-2"),
        dcc.Dropdown(id="tier-dropdown",
                     options=[{"label": f"Tier {int(t)}", "value": t} for t in tiers],
                     value=[], multi=True, placeholder="Select tiers...",
                     className="mb-3"),
    ]),
    html.Hr(),

    html.Div([
        dbc.Button("Clear All Filters", id="clear-filters-btn",
                   color="outline-secondary", size="sm", className="mb-3"),
    ]),
    html.Div([
        html.H6("Stats", className="text-primary mb-3"),
        html.Div(id="filter-stats"),
    ]),
], style=SIDEBAR_STYLE)

content = html.Div([
    html.Div([
        html.H1("EJM Applicant Registration Dashboard",
                className="text-center mb-4",
                style={"font-weight": "300", "letter-spacing": "2px"}),
    ], className="mb-5"),
    html.Div([
        html.H3("Registration Overview", className="mb-3"),
        html.Div(id="chart-subtitle", className="mb-2"),
        dcc.Graph(id="registration-graph", style={"height": "70vh"}),
    ]),
], style=CONTENT_STYLE)

footer = html.Div([
    html.Div([
        html.Img(
            src="https://leap.unibocconi.eu/newsevents/one-post-doctoral-research-position-leap",
            style={"height": "25px", "margin-right": "15px"},
        ),
        html.Span("\u00a9 Dhruva Devaraaj.", className="text-muted small"),
    ], style={"display": "flex", "align-items": "center"}),
], style=FOOTER_STYLE)

app.layout = html.Div([sidebar, content, footer])

# ==========================================================================
# Callbacks
# ==========================================================================

@callback(
    Output("year-dropdown", "options"),
    [Input("date-field-selector", "value")],
)
def update_year_options(date_field):
    years = academic_years if date_field == "enrolldate" else login_academic_years
    return [{"label": f"{int(y)}-{int(y)+1}", "value": y} for y in years]


@callback(
    [Output("year-dropdown", "value"),
     Output("degreetype-dropdown", "value"),
     Output("primary-field-dropdown", "value"),
     Output("country-dropdown", "value"),
     Output("tier-dropdown", "value")],
    [Input("clear-filters-btn", "n_clicks")],
)
def clear_filters(_):
    return [], [], [], [], []


@callback(
    Output("filter-stats", "children"),
    [Input("date-field-selector", "value"),
     Input("year-dropdown", "value"),
     Input("degreetype-dropdown", "value"),
     Input("primary-field-dropdown", "value"),
     Input("country-dropdown", "value"),
     Input("tier-dropdown", "value")],
)
def update_filter_stats(date_field, sel_years, sel_degrees, sel_fields,
                        sel_countries, sel_tiers):
    filtered = filter_data(registration_data, sel_years, sel_degrees,
                           sel_fields, sel_countries, sel_tiers, date_field)
    year_col = DATE_FIELDS[date_field]["year_col"]
    n = len(filtered)

    elements = [
        html.P([html.Strong("Total: "),
                html.Span(f"{n:,}", className="text-success")], className="mb-2"),
        html.P([html.Strong("% of Total: "),
                html.Span(f"{n / total_registrations * 100:.1f}%",
                          className="text-primary")], className="mb-2"),
    ]

    if sel_years:
        years_to_show = sorted(sel_years, reverse=True)
    elif len(filtered) > 0:
        years_to_show = sorted(filtered[year_col].unique(), reverse=True)
    else:
        years_to_show = []

    for year in years_to_show:
        count = len(filtered[filtered[year_col] == year])
        elements.append(
            html.P([html.Strong(f"{int(year)}-{int(year)+1}: "),
                    html.Span(f"{count:,}", className="text-info")],
                   className="mb-1 small")
        )

    return elements


@callback(
    Output("chart-subtitle", "children"),
    [Input("date-field-selector", "value")],
)
def update_chart_subtitle(date_field):
    label = DATE_FIELDS[date_field]["label"].lower()
    return html.P(f"Growth curve based on {label}", className="text-muted small")


@callback(
    Output("registration-graph", "figure"),
    [Input("date-field-selector", "value"),
     Input("year-dropdown", "value"),
     Input("degreetype-dropdown", "value"),
     Input("primary-field-dropdown", "value"),
     Input("country-dropdown", "value"),
     Input("tier-dropdown", "value")],
)
def update_graph(date_field, sel_years, sel_degrees, sel_fields,
                 sel_countries, sel_tiers):
    filtered = filter_data(registration_data, sel_years, sel_degrees,
                           sel_fields, sel_countries, sel_tiers, date_field)
    filtered = filtered.dropna(subset=[date_field])

    if filtered.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available for selected filters",
                          xaxis_title="Time", yaxis_title="Cumulative Count")
        return fig

    year_col = DATE_FIELDS[date_field]["year_col"]
    label = DATE_FIELDS[date_field]["label"]
    years_to_show = sorted(sel_years if sel_years else filtered[year_col].unique())

    fig = go.Figure(data=build_traces(filtered, date_field, year_col, years_to_show))

    fig.update_layout(
        title=make_title(label, sel_years),
        xaxis_title="Timeline",
        yaxis_title="Cumulative Count",
        showlegend=True,
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=academic_xaxis(),
        yaxis=dict(showgrid=True, gridcolor="lightgray"),
        height=600,
    )

    return fig

# ==========================================================================
# Server
# ==========================================================================

server = app.server

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
