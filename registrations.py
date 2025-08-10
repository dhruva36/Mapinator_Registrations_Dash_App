from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px
import pandas as pd
import numpy as np
import json
from flask import Flask
import requests
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

load_figure_template('LUX')
app_server = Flask(__name__)
app = Dash(__name__, server=app_server,external_stylesheets=[dbc.themes.LUX])

# Load Data
r = requests.get('https://support.econjobmarket.org/api/registrations')

registration_data = pd.DataFrame(r.json())

# Preprocess Data
registration_data['enrolldate'] = pd.to_datetime(registration_data['enrolldate'])
registration_data['date_last_login'] = pd.to_datetime(registration_data['date_last_login'])

cutoff_date = pd.to_datetime('2021-06-01')
registration_data = registration_data[registration_data['enrolldate'] >= cutoff_date]
registration_data = registration_data[registration_data['date_last_login'] >= cutoff_date]

# Date -> Year Conversion
def get_academic_year(date):

    if date.month >= 6:  
        return date.year
    else:  
        return date.year - 1

registration_data['academic_year'] = registration_data['enrolldate'].apply(get_academic_year)
registration_data['login_academic_year'] = registration_data['date_last_login'].apply(get_academic_year)
registration_data['enroll_year'] = registration_data['enrolldate'].dt.year


# Dropdown 
primary_fields = sorted([x for x in registration_data['primary_field'].unique() if x is not None])
countries = sorted([x for x in registration_data['country'].unique() if x is not None])
tiers = sorted([x for x in registration_data['tier'].unique() if x is not None and not pd.isna(x)])
degree_types = sorted([x for x in registration_data['degreetype'].unique() if x is not None])
academic_years = sorted([x for x in registration_data['academic_year'].unique() if x is not None and not pd.isna(x)])
login_academic_years = sorted([x for x in registration_data['login_academic_year'].unique() if x is not None and not pd.isna(x)])

# Summary
total_registrations = len(registration_data)

# Formatting
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "18rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
    "border-right": "1px solid #dee2e6",
    "overflow-y": "auto"
}

CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    "padding-bottom": "4rem",  
}

FOOTER_STYLE = {
    "position": "fixed",
    "left": "18rem",
    "right": 0,
    "bottom": 0,
    "height": "3rem",
    "background-color": "#f8f9fa",
    "border-top": "1px solid #dee2e6",
    "padding": "0.5rem 2rem",
    "display": "flex",
    "align-items": "center",
    "justify-content": "center"
}

# Sidebar
sidebar = html.Div([
    html.H4("FILTERS", className="text-primary mb-4"),
   html.P("Select Characteristics", className="text-muted small mb-4"),
    
    html.Hr(),
    
    # Enrollment/Login Selector
    html.Div([
        html.Label("View by", className="form-label fw-bold mb-2"),
        dcc.RadioItems(
            id='date-field-selector',
            options=[
                {'label': ' Enrollment Date', 'value': 'enrolldate'},
                {'label': ' Last Login Date', 'value': 'date_last_login'}
            ],
            value='enrolldate',
            className="mb-3",
            labelStyle={'display': 'block', 'margin-bottom': '5px'}
        )
    ]),
    
    html.Hr(),
    
    # Year Filter 
    html.Div([
        html.Label("Academic Year", className="form-label fw-bold mb-2"),
        dcc.Dropdown(
            id='year-dropdown',
            options=[],  
            value=[],
            multi=True,
            placeholder="Select academic years...",
            className="mb-3"
        )
    ]),
    
    # Degree Filter
    html.Div([
        html.Label("Degree Type", className="form-label fw-bold mb-2"),
        dcc.Dropdown(
            id='degreetype-dropdown',
            options=[{'label': dtype, 'value': dtype} for dtype in degree_types],
            value=[],
            multi=True,
            placeholder="Select degree types...",
            className="mb-3"
        )
    ]),
    
    # Field Filter
    html.Div([
        html.Label("Primary Field", className="form-label fw-bold mb-2"),
        dcc.Dropdown(
            id='primary-field-dropdown',
            options=[{'label': field, 'value': field} for field in primary_fields],
            value=[],
            multi=True,
            placeholder="Select fields...",
            className="mb-3"
        )
    ]),
    
    # Country Filter
    html.Div([
        html.Label("Country", className="form-label fw-bold mb-2"),
        dcc.Dropdown(
            id='country-dropdown',
            options=[{'label': country, 'value': country} for country in countries],
            value=[],
            multi=True,
            placeholder="Select countries...",
            className="mb-3"
        )
    ]),
    
    # Tier Filter
    html.Div([
        html.Label("University Tier", className="form-label fw-bold mb-2"),
        dcc.Dropdown(
            id='tier-dropdown',
            options=[{'label': f"Tier {int(tier)}", 'value': tier} for tier in tiers],
            value=[],
            multi=True,
            placeholder="Select tiers...",
            className="mb-3"
        )
    ]),
    
    html.Hr(),
    
    # Clear Filters 
    html.Div([
        dbc.Button(
            "Clear All Filters",
            id="clear-filters-btn",
            color="outline-secondary",
            size="sm",
            className="mb-3"
        )
    ]),
    
    # Summary Stats
    html.Div([
        html.H6("Stats", className="text-primary mb-3"),
        html.Div(id="filter-stats")
    ])
    
], style=SIDEBAR_STYLE)

content = html.Div([
    # Header
    html.Div([
        html.H1("EJM Applicant Registration Dashboard", 
                className="text-center mb-4", 
                style={"font-weight": "300", "letter-spacing": "2px"}),
    ], className="mb-5"),
    
    # Graph Section
    html.Div([
        html.H3("Registration Overview", className="mb-3"),
        html.Div(id="chart-subtitle", className="mb-2"),
        dcc.Graph(id='registration-graph', style={'height': '70vh'})
    ])
    
], style=CONTENT_STYLE)

# Footer
footer = html.Div([
    html.Div([
        html.Img(
            src="https://leap.unibocconi.eu/newsevents/one-post-doctoral-research-position-leap",
            style={"height": "25px", "margin-right": "15px"}  
        ),
        html.Span("© Dhruva Devaraaj.", 
                 className="text-muted small")
    ], style={"display": "flex", "align-items": "center"})
], style=FOOTER_STYLE)

# Layout
app.layout = html.Div([sidebar, content, footer])

# Filter data
def filter_data(data, selected_years, degree_types, primary_fields, countries, tiers, date_field):
    filtered_data = data.copy()
    
    if selected_years:
        if date_field == 'enrolldate':
            # Filter by enrollment
            filtered_data = filtered_data[filtered_data['academic_year'].isin(selected_years)]
        else:
            # Filter by login
            filtered_data = filtered_data[filtered_data['login_academic_year'].isin(selected_years)]
    
    if degree_types:
        filtered_data = filtered_data[filtered_data['degreetype'].isin(degree_types)]
    
    if primary_fields:
        filtered_data = filtered_data[filtered_data['primary_field'].isin(primary_fields)]
    
    if countries:
        filtered_data = filtered_data[filtered_data['country'].isin(countries)]
    
    if tiers:
        filtered_data = filtered_data[filtered_data['tier'].isin(tiers)]
    
    return filtered_data

# Year Callback
@callback(
    Output('year-dropdown', 'options'),
    [Input('date-field-selector', 'value')]
)
def update_year_options(selected_date_field):
    if selected_date_field == 'enrolldate':
        # enrollment  
        return [{'label': f"{int(year)}-{int(year)+1}", 'value': year} for year in academic_years]
    else:
        # login 
        return [{'label': f"{int(year)}-{int(year)+1}", 'value': year} for year in login_academic_years]

# Clear Filter Callback
@callback(
    [Output('year-dropdown', 'value'),
     Output('degreetype-dropdown', 'value'),
     Output('primary-field-dropdown', 'value'),
     Output('country-dropdown', 'value'),
     Output('tier-dropdown', 'value')],
    [Input('clear-filters-btn', 'n_clicks')]
)
def clear_filters(n_clicks):
    if n_clicks:
        return [], [], [], [], []
    return [], [], [], [], []

# Filter Stats Callback
@callback(
    Output('filter-stats', 'children'),
    [Input('date-field-selector', 'value'),
     Input('year-dropdown', 'value'),
     Input('degreetype-dropdown', 'value'),
     Input('primary-field-dropdown', 'value'),
     Input('country-dropdown', 'value'),
     Input('tier-dropdown', 'value')]
)
def update_filter_stats(selected_date_field, selected_years, selected_degree_types, selected_fields, selected_countries, selected_tiers):
    filtered_data = filter_data(registration_data, selected_years, selected_degree_types, 
                               selected_fields, selected_countries, selected_tiers, selected_date_field)
    
    filtered_total = len(filtered_data)
    
    if not selected_years:
        stats_elements = [
            html.P([
                html.Strong("Total: "),
                html.Span(f"{filtered_total:,}", className="text-success")
            ], className="mb-2"),
            html.P([
                html.Strong("% of Total: "),
                html.Span(f"{(filtered_total/total_registrations*100):.1f}%", className="text-primary")
            ], className="mb-2"),
        ]
        
        if len(filtered_data) > 0:
            if selected_date_field == 'enrolldate':
                year_breakdown = filtered_data.groupby('academic_year').size().sort_index(ascending=False)
            else:
                year_breakdown = filtered_data.groupby('login_academic_year').size().sort_index(ascending=False)
                
            for year, count in year_breakdown.items():
                stats_elements.append(
                    html.P([
                        html.Strong(f"{int(year)}-{int(year)+1}: "),
                        html.Span(f"{count:,}", className="text-info")
                    ], className="mb-1 small")
                )
    else:
        stats_elements = [
            html.P([
                html.Strong("Total: "),
                html.Span(f"{filtered_total:,}", className="text-success")
            ], className="mb-2"),
            html.P([
                html.Strong("% of Total: "),
                html.Span(f"{(filtered_total/total_registrations*100):.1f}%", className="text-primary")
            ], className="mb-2"),
        ]
        
        for year in sorted(selected_years, reverse=True):
            if selected_date_field == 'enrolldate':
                year_count = len(filtered_data[filtered_data['academic_year'] == year])
            else:
                year_count = len(filtered_data[filtered_data['login_academic_year'] == year])
                
            stats_elements.append(
                html.P([
                    html.Strong(f"{int(year)}-{int(year)+1}: "),
                    html.Span(f"{year_count:,}", className="text-info")
                ], className="mb-1 small")
            )
    
    return stats_elements


@callback(
    Output('chart-subtitle', 'children'),
    [Input('date-field-selector', 'value')]
)
def update_chart_subtitle(selected_date_field):
    if selected_date_field == 'enrolldate':
        return html.P("Growth curve based on enrollment date", className="text-muted small")
    else:
        return html.P("Growth curve based on last login date", className="text-muted small")

# Graph Callback
@callback(
    Output('registration-graph', 'figure'),
    [Input('date-field-selector', 'value'),
     Input('year-dropdown', 'value'),
     Input('degreetype-dropdown', 'value'),
     Input('primary-field-dropdown', 'value'),
     Input('country-dropdown', 'value'),
     Input('tier-dropdown', 'value')]
)
def update_graph(selected_date_field, selected_years, selected_degree_types, 
                selected_fields, selected_countries, selected_tiers):
    
    filtered_data = filter_data(registration_data, selected_years, selected_degree_types,
                               selected_fields, selected_countries, selected_tiers, selected_date_field)
    
    filtered_data = filtered_data.dropna(subset=[selected_date_field])
    
    if len(filtered_data) == 0:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data available for selected filters",
            xaxis_title="Time",
            yaxis_title="Cumulative Count"
        )
        return empty_fig
    
    combined_fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Enrollment Date 
    if selected_date_field == 'enrolldate':
        if not selected_years:
            years_to_show = sorted(filtered_data['academic_year'].unique())
        else:
            years_to_show = selected_years
        
        for i, academic_year in enumerate(years_to_show):
            year_data = filtered_data[filtered_data['academic_year'] == academic_year].copy()
            
            if len(year_data) > 0:
                year_data = year_data.sort_values(selected_date_field).reset_index(drop=True)
                year_data['cumulative_count'] = np.arange(1, len(year_data) + 1)
                
                def date_to_academic_days(date, academic_year):
                    academic_start = pd.Timestamp(year=int(academic_year), month=6, day=1)
                    return (date - academic_start).days
                
                academic_timeline = [date_to_academic_days(row[selected_date_field], academic_year) 
                                   for _, row in year_data.iterrows()]
                
                combined_fig.add_trace(go.Scatter(
                    x=academic_timeline,
                    y=year_data['cumulative_count'],
                    name=f'{int(academic_year)}-{int(academic_year)+1}',
                    mode='lines+markers',
                    marker=dict(size=4),
                    line=dict(width=2, color=colors[i % len(colors)])
                ))
        
        # x-axis months
        academic_month_names = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']
        academic_month_positions = [0, 30, 61, 92, 122, 153, 183, 214, 245, 273, 304, 334]
        
        xaxis_title = "Timeline"
        xaxis_config = dict(
            tickmode='array',
            tickvals=academic_month_positions,
            ticktext=academic_month_names,
            showgrid=True,
            gridcolor='lightgray',
            range=[0, 365]
        )
        
        if not selected_years:
            title_text = "Cumulative Count by Enrollment Date - All Years"
        elif len(selected_years) == 1:
            year = selected_years[0]
            title_text = f"Cumulative Count by Enrollment Date - {int(year)}-{int(year)+1}"
        else:
            title_text = "Cumulative Count by Enrollment Date - Years"
    
    # Last Login 
    else:
        if not selected_years:
            login_years_to_show = sorted(filtered_data['login_academic_year'].unique())
            
            for i, login_academic_year in enumerate(login_years_to_show):
                year_data = filtered_data[filtered_data['login_academic_year'] == login_academic_year].copy()
                
                if len(year_data) > 0:
                    year_data = year_data.sort_values(selected_date_field).reset_index(drop=True)
                    year_data['cumulative_count'] = np.arange(1, len(year_data) + 1)
                    
                    # Convert to timeline 
                    def date_to_academic_days(date, academic_year):
                        academic_start = pd.Timestamp(year=int(academic_year), month=6, day=1)
                        return (date - academic_start).days
                    
                    academic_timeline = [date_to_academic_days(row[selected_date_field], login_academic_year) 
                                       for _, row in year_data.iterrows()]
                    
                    combined_fig.add_trace(go.Scatter(
                        x=academic_timeline,
                        y=year_data['cumulative_count'],
                        name=f'{int(login_academic_year)}-{int(login_academic_year)+1}',
                        mode='lines+markers',
                        marker=dict(size=4),
                        line=dict(width=2, color=colors[i % len(colors)])
                    ))
            
            title_text = "Cumulative Count by Last Login Date - All Years"
            xaxis_title = "Timeline"
            
            academic_month_names = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']
            academic_month_positions = [0, 30, 61, 92, 122, 153, 183, 214, 245, 273, 304, 334]
            
            xaxis_config = dict(
                tickmode='array',
                tickvals=academic_month_positions,
                ticktext=academic_month_names,
                showgrid=True,
                gridcolor='lightgray',
                range=[0, 365]
            )
        
        else:
            for i, login_academic_year in enumerate(selected_years):
                year_data = filtered_data[filtered_data['login_academic_year'] == login_academic_year].copy()
                
                if len(year_data) > 0:
                    year_data = year_data.sort_values(selected_date_field).reset_index(drop=True)
                    year_data['cumulative_count'] = np.arange(1, len(year_data) + 1)
                    
                    # Convert to timeline 
                    def date_to_academic_days(date, academic_year):
                        academic_start = pd.Timestamp(year=int(academic_year), month=6, day=1)
                        return (date - academic_start).days
                    
                    academic_timeline = [date_to_academic_days(row[selected_date_field], login_academic_year) 
                                       for _, row in year_data.iterrows()]
                    
                    combined_fig.add_trace(go.Scatter(
                        x=academic_timeline,
                        y=year_data['cumulative_count'],
                        name=f'{int(login_academic_year)}-{int(login_academic_year)+1}',
                        mode='lines+markers',
                        marker=dict(size=4),
                        line=dict(width=2, color=colors[i % len(colors)])
                    ))
            
            if len(selected_years) == 1:
                year = selected_years[0]
                title_text = f"Cumulative Count by Last Login Date - {int(year)}-{int(year)+1}"
            else:
                title_text = "Cumulative Count by Last Login Date - Selected Years"
            
            xaxis_title = "Timeline"
            
            academic_month_names = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May']
            academic_month_positions = [0, 30, 61, 92, 122, 153, 183, 214, 245, 273, 304, 334]
            
            xaxis_config = dict(
                tickmode='array',
                tickvals=academic_month_positions,
                ticktext=academic_month_names,
                showgrid=True,
                gridcolor='lightgray',
                range=[0, 365]
            )
    
    combined_fig.update_layout(
        title=title_text,
        xaxis_title=xaxis_title,
        yaxis_title="Cumulative Count",
        showlegend=True,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=xaxis_config,
        yaxis=dict(showgrid=True, gridcolor='lightgray'),
        height=600
    )
    
    return combined_fig

server = app.server

if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0', port=8050)
