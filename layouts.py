from math import log10
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
# Local imports
from __init__ import VERSION, DEFAULT_TICKER, DEFAULT_SNAPSHOT_UUID
from dash_utils import make_card, ticker_inputs, make_item, make_social_media_share
from dynamic_layouts import get_dcf_current_year_input_overrides, get_other_input_overrides
from assets.about import source_credits, assumptions
from assets.disclaimer import disclaimer

# Reference and some Dashboard components inspired by: https://medium.com/swlh/how-to-create-a-dashboard-to-dominate-the-stock-market-using-python-and-dash-c35a12108c93

navheader = dbc.Row([dbc.Col(
                        dbc.Nav([
                        dbc.NavLink("Main", href="/", id='nav-main'),
                        dbc.NavLink("DCF Valuation Analysis", href="/apps/dcf/AAPL", id='nav-dcf'),
                        dbc.NavLink("Sector Value Analysis", href="/apps/sector", id='nav-sector'),
                        ], pills=True),
                        ),
                    dbc.Col(id='social-share', align='right', width=400),
                    dbc.Col([html.Small('VERSION:'), html.P(VERSION)], align='right', width=60)
            ])



tabheader = html.Div([
        dbc.Tabs([
                dbc.Tab(label="DCF Valuation Analysis", tab_id="tab-dcf"),
                dbc.Tab(label="Sector Value Analysis", tab_id="tab-sector"),
            ],
            id="tabs",
            active_tab="tab-dcf",
        ),
        html.Div(id="tab-content"),
    ])

dcflayout = html.Div([
    navheader,
    # html.H3('DCF Valuation Analysis'),
    # MD text area Element for Introduction
    dbc.Row([dbc.Col(
        [dcc.Markdown(children='''
            ### Purpose of this web app ###
            ##### To be one of the tools to educate and democratize fundamentals DCF (Discounted Cash Flow) Valuation Analysis of public equity investments #####
            See below for more details, Assumptions and Disclaimer or visit [About this DCF Valuation App](https://codepatel.github.io/dcf/)
            '''
        )],
        ),
    ]), # heading row
    dbc.Row([
        dbc.Col([
        make_card("Ticker for Analysis", "info", [ticker_inputs('ticker-input', 'date-picker', 12*5),
            # dbc.Select(
            #     id='ticker-input', 
            #     options=[{'label': s['symbol']+'('+s['exchange']+'):'+s['name'], 'value': s['symbol']} for s in symdata],
            #     value='AAPL',
            #     placeholder='Start typing Ticker, press Enter'),
            dbc.FormGroup(
                    [
                        dbc.Label("Analysis mode selection: (if inactive, use Snapshot mode)"),
                        dbc.Checklist(
                        options=[
                            {"label": "Live?", "value": 1},
                        ],
                        value=[1],
                        id="analysis-mode",
                        switch=True,
                        ),
                    ]
            ),
            html.Data(id='snapshot-uuid', value=DEFAULT_SNAPSHOT_UUID), 
            html.Div([dbc.Button('Save Snapshot', id='save-snapshot', color='primary'),
                html.Span(dbc.NavLink('Snapshot Link to Bookmark', id='snapshot-link', href='/apps/dcf/'+DEFAULT_TICKER+'/'+DEFAULT_SNAPSHOT_UUID, disabled=True), style={"vertical-align": "middle"}),
                ]),
        ]), 
        html.Div(id='ticker-allcaps'), 
        
        make_card('Status Message', 'success', dbc.Spinner(html.P(id='status-info', loading_state={'is_loading': True}), fullscreen=False)),
        make_card('Supplemental Info', 'success', dbc.Spinner([html.P(id='supp-info'),
            dcc.Store(id='fin-store'),
            dcc.Store(id='dcf-store'),
            dcc.Store(id='topsstream-data'),
            dcc.Store(id="handler-parseURL"),
            dcc.Store(id="handler-ticker-valid"),
            dcc.Store(id="handler-past-data"), 
            dcc.Store(id="handler-dcf-data"),            
            dcc.Store(id='handler-lastpricestream'),
            dcc.Interval(
                id='price-update-interval',
                interval=15*1000, # in milliseconds
                n_intervals=0
            )
            ]))
        ]),
        dbc.Col([
        make_card('DCF Inputs - Company factors', 'info', dbc.Tabs([
                dbc.Tab(
                    dbc.Form([
                        dbc.Label("Revenue Growth Rate (%) for next year", html_for="rgr-next"),
                        dbc.Input(id="rgr-next", type="number", value=0, min=-50, step=0.1, placeholder="Enter number", debounce=True
                                ),
                        dbc.Label("Operating Margin (%) for next year excl. Reinvestment", html_for="opm-next"),
                        dbc.Input(id="opm-next", type="number", value=0, max=50, step=0.1, placeholder="Enter number", debounce=True
                                ),
                        html.Br(),
                        dbc.Label("CAGR (%) for years 2-5 (select range: 0 to 15)", html_for="cagr-2-5"),
                        dcc.Slider(id="cagr-2-5", min=0, max=15, step=0.1, value=5, 
                        tooltip={'always_visible': True, 'placement': 'topRight'},
                        marks={v: str(v) for v in range(0, 16)}),
                        dbc.Label("Target Pre-Tax Operating Margin (%) in business model (select range: 0 to 50)", html_for="opm-target"),
                        dcc.Slider(id="opm-target", min=0, max=50, step=0.1, value=20, 
                        tooltip={'always_visible': True, 'placement': 'topRight'},
                        marks={v: str(v) for v in range(0, 55, 5)}),
                        dbc.Label("Sales to capital ratio (for computing reinvestment, select range: 0 to 5)", html_for="sales-to-cap"),
                        dcc.Slider(id="sales-to-cap", min=0, max=5, step=0.01, value=1, 
                        tooltip={'always_visible': True, 'placement': 'topRight'},
                        marks={v: str(v) for v in range(0, 6)}),
                    ]), label="GPE Levers", tab_id="tab-lever", label_style={"color": "#00AEF9"}
                ),
                dbc.Tab(
                    dbc.Form([
                        html.P('In future, calculate Equity Risk Premium based on discrete inputs. For now, enter ERP:'),
                        html.Br(),
                        dbc.Label("Equity Risk Premium (%)", html_for="erp-calculated"),
                        dbc.Input(id="erp-calculated", type="number", value=6, min=0, max=10, step=0.01, placeholder="Enter number", debounce=True
                                ),
                    ]), label="ERP Calculation", tab_id="tab-erp", label_style={"color": "#00AEF9"}
                ),
            ], id="company-tabs", active_tab="tab-lever",
            ))
        ]),
        dbc.Col([
        make_card('DCF Inputs - Environmental factors', 'info', dbc.Form([
            dbc.Label("Effective Tax Rate (%) (select range: 0 to 30)", html_for="tax-rate"),
            dcc.Slider(id="tax-rate", min=0, max=30, step=0.1, value=15, 
            tooltip={'always_visible': True, 'placement': 'topRight'},
            marks={v: str(v) for v in range(0, 35, 5)}),
            dbc.Label("Riskfree Rate (%) (select range: 0 to 5)", html_for="riskfree-rate"),
            dcc.Slider(id="riskfree-rate", min=0, max=5, step=0.25, value=1.25, 
            tooltip={'always_visible': True, 'placement': 'topRight'},
            marks={v: str(v) for v in range(0, 6)}),
            dbc.Label("Terminal Growth Rate (%) (select range: 0 to 5)", html_for="terminal-growth-rate"),
            dcc.Slider(id="terminal-growth-rate", min=0, max=5, step=0.25, value=3.5, 
            tooltip={'always_visible': True, 'placement': 'topRight'},
            marks={v: str(v) for v in range(0, 6)}, disabled=False),
            dbc.Label("Cost of Capital / Discount Rate (%) (select range: 0 to 15)", html_for="cost-of-cap"),
            dcc.Slider(id="cost-of-cap", min=0, max=15, step=0.25, value=8.5, 
            tooltip={'always_visible': True, 'placement': 'topRight'},
            marks={v: str(v) for v in range(0, 16)}),
        ])),
        make_card('DCF Outputs', 'success', dbc.Spinner(html.Div(id="dcf-data")))
        ]),
    ]), #row 1
    # Element for Graph plot of KPIndicators
    dbc.Row([
        dbc.Col([
            make_card("Past records Financial table (Current Year is TTM/MRQ) ", "secondary", 
            dbc.Spinner(html.Div(id="fin-table"))),              
            html.Small('Data source: https://www.marketwatch.com/ Copyright 2020 FactSet Research Systems Inc. All rights reserved. Source FactSet Fundamentals')
        ]),
        dbc.Col([html.Div([
        html.H6('Select Parameter(s) to show trend over the past periods'),
        dcc.Dropdown(
                id='select-column',
                value=['ROCE(%)', 'Sales-to-Capital(%)', 'Net Profit Margin(%)', 'Revenue Growth(%)'],
                multi=True
        ),
        dbc.Spinner(dcc.Graph(
            id='plot-indicators'
        ))])
        ]),
        
    ]), # row 2
    dbc.Row([
        dbc.Col(make_card("Current Year Input (Use Latest 10K/10Q to Override)", "warning", 
            get_dcf_current_year_input_overrides())
        ),
        dbc.Col(make_card("Other Input Overrides", "warning", 
            [get_other_input_overrides(),
            html.Br(),
            dcc.Markdown(children='''
            **Other Assumptions for Intrinsic Value DCF Valuation:**\n
                1. TERMINAL_YEAR_LENGTH = 10
                2. No Preferred stock/dividends in capital structure (you can override this)
                3. No Convertible debt/equity portion in capital structure (you can override this)
            '''),
            dbc.Button("Run DCF calculation again with overrides", id='run-dcf', color='primary', block=True),
            make_card("DCF table (2-stage Terminal value after 10 years) ", "secondary", 
            dbc.Spinner(html.Div(id="dcf-table")))
        ])),
        dbc.Col([
            make_card("Notes/Commentary", "primary",
            dbc.Textarea(bs_size="lg", placeholder='Enter your notes and commentary on the analysis')
            )
        ])
    ],form=True), # row 3
    dbc.Row([
        dbc.Col([
            
        ]),
    ]), # row 4
    dbc.Row([dbc.Col(
        # MD text area Element for interpretation and analysis of data
        dcc.Markdown(children=source_credits + assumptions + disclaimer)
        )
    ])  # footer row
])

sectorlayout = html.Div([
    navheader,
    # html.H3('Sector Value Analysis'),
    # MD text area Element for Introduction
    dbc.Row([dbc.Col(
        [dcc.Markdown(children='''
            ### Find the best picks in the sector! ###
            '''
        )],
        ),  
    ]), # heading row
    html.Div(id='sector-app-display-value', children="Under Construction! Features may change without notice!", style={'backgroundColor': 'red', 'fontSize': '200%'}),
    html.Br(),
    dbc.NavLink('IEX Cloud is the easiest way to use financial data. Get started now by clicking this referral link!', href="https://iexcloud.io/s/b47b5006"),
    html.Br(),
    html.P("Please note that sandbox test response data shown below from IEX Cloud Sandbox APIs is purposefully manipulated to scramble values and is not suitable for production usage. Data returned in the sandbox will look real, but strings are scrambled, dates are manipulated, and numbers are changed.", style={'color': 'red'}),
    dbc.NavLink('See this link for more information on Sandbox Testing', href="https://iexcloud.io/docs/api/#testing-sandbox"),
    html.Br(),

    dcc.Store(id='sector-store'),
    # Element for Graph plot of Sector Picks
    dbc.Row([
        dbc.Col([html.Div([
        html.H5('Select Sector(s): '),
        dcc.Dropdown(
                id='select-sector',
                options=[{'label': i, 'value': i} for i in ["Electronic Technology",
                       "Distribution Services",
                       "Health Technology",
                       "Commercial Services",
                       "Industrial Services",
                       "Finance",
                       "Process Industries",
                       "Transportation",
                       "Technology Services",
                       "Producer Manufacturing",
                       "Retail Trade",
                       "Consumer Services",
                       "Non-Energy Minerals",
                       "Utilities",
                       "Miscellaneous",
                       "Health Services",
                       "Consumer Durables",
                       "Consumer Non-Durables",
                       "Communications",
                       "Energy Minerals",
                       "Government"]],
                value=["Electronic Technology", "Health Technology", "Technology Services"],
                multi=True
        ),
        
        ])
        ]),
    ]), # row 1
    dbc.Row([
        dbc.Col([
            html.Br(),
            dcc.Dropdown(
                id='select-company',
                value=[],
                multi=True,
                placeholder='Filter to one or more companies, start typing in dropdown'
            ),
            dbc.Label("Filter by Enterprise Value (in billions)", html_for="sector-ev-filter"),
            dcc.RangeSlider(id="sector-ev-filter", min=7, max=13, step=0.001, value=[8, 12.699], 
            marks={i: str(10 ** (i-9))+'B' for i in range(7, 14)},
            updatemode='drag',
            ),
            html.H5('Crossfilter-Yaxis'),
            dcc.Dropdown(
                id='crossfilter-yaxis-column',
                value='EBITDAToRevenueMargin',
            ),
        ], width=3),
        dbc.Col([
            dbc.NavLink('Data provided by IEX Cloud', href="https://iexcloud.io"),
            dbc.Spinner(dcc.Graph(id='sector-distribution'
            )),
            html.H5('Crossfilter-Xaxis'),
            dcc.Dropdown(
                id='crossfilter-xaxis-column',
                value='EBITDAToEV(%)',
            ),
        ])
    ]), # row 2
    dbc.Row([dbc.Col(
        # MD text area Element for footer
        dcc.Markdown(children=disclaimer)
        )
    ])  # footer row
])
