import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
# Local imports
from dash_utils import make_card, ticker_inputs, make_item, make_social_media_share
from dynamic_layouts import get_dcf_current_year_input_overrides, get_other_input_overrides

# Reference and some Dashboard components inspired by: https://medium.com/swlh/how-to-create-a-dashboard-to-dominate-the-stock-market-using-python-and-dash-c35a12108c93

navheader = dbc.Nav([
                dbc.NavLink("DCF Valuation Analysis", href="/apps/dcf"),
                dbc.NavLink("Sector Value Analysis", href="/apps/sector"),
            ], pills=True)

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
            See footer below for more on [About this DCF Valuation App](#about-this-app), Disclaimer and Assumptions
            '''
        )],
        ),
        dbc.Col(make_social_media_share(), align='right', width=400
        )
    ]), # heading row
    dbc.Row([
        dbc.Col([
        make_card("Enter Ticker", "info", ticker_inputs('ticker-input', 'date-picker', 12*5)
        # dbc.Select(
        #     id='ticker-input', 
        #     options=[{'label': s['symbol']+'('+s['exchange']+'):'+s['name'], 'value': s['symbol']} for s in symdata],
        #     value='AAPL',
        #     placeholder='Start typing Ticker, press Enter')
        ), html.Div(id='ticker-allcaps'),
        make_card('Status Message', 'success', dbc.Spinner(html.P(id='status-info', children='Updating...'))),
        make_card('Supplemental Info', 'success', dbc.Spinner(html.P(id='supp-info', children='Updating...')))
        ]),
        dbc.Col([
        make_card('DCF Inputs - Company factors', 'info', dbc.Tabs([
                dbc.Tab(
                    dbc.Form([
                        dbc.Label("Revenue Growth Rate (%) for next year", html_for="rgr-next"),
                        dbc.Input(id="rgr-next", type="number", value=0, min=-50, step=1, placeholder="Enter number", debounce=True
                                ),
                        dbc.Label("Operating Margin (%) for next year excl. Reinvestment", html_for="opm-next"),
                        dbc.Input(id="opm-next", type="number", value=10, max=50, step=1, placeholder="Enter number", debounce=True
                                ),
                        html.Br(),
                        dbc.Label("CAGR (%) for years 2-5 (select range: 0 to 15)", html_for="cagr-2-5"),
                        dcc.Slider(id="cagr-2-5", min=0, max=15, step=0.1, value=5, 
                        tooltip={'always_visible': True, 'placement': 'topRight'}),
                        dbc.Label("Target Pre-Tax Operating Margin (%) in business model (select range: 0 to 50)", html_for="opm-target"),
                        dcc.Slider(id="opm-target", min=0, max=50, step=0.1, value=20, 
                        tooltip={'always_visible': True, 'placement': 'topRight'}),
                        dbc.Label("Sales to capital ratio (for computing reinvestment, select range: 0 to 4)", html_for="sales-to-cap"),
                        dcc.Slider(id="sales-to-cap", min=0, max=4, step=0.05, value=1, 
                        tooltip={'always_visible': True, 'placement': 'topRight'}),
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
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Riskfree Rate (%) (select range: 0 to 5)", html_for="riskfree-rate"),
            dcc.Slider(id="riskfree-rate", min=0, max=5, step=0.25, value=3.5, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Cost of Capital (%) (select range: 0 to 15)", html_for="cost-of-cap"),
            dcc.Slider(id="cost-of-cap", min=0, max=15, step=0.25, value=8.5, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
        ])),
        make_card('DCF Outputs', 'success', dbc.Spinner(html.Div(id="dcf-data")))
        ]),
    ]), #row 1
    # Element for Graph plot of KPIndicators
    dbc.Row([
        dbc.Col([
            make_card("Past records Financial table (Current Year is TTM/MRQ) ", "secondary", 
            dbc.Spinner(html.Div(id="fin-table"))),  
            dt.DataTable(id="fin-df"),
            dt.DataTable(id="stats-df"),
            dt.DataTable(id="handler-ticker-valid"),
            dt.DataTable(id="handler-past-data"), 
            dt.DataTable(id="handler-dcf-data"),
            html.Small('Data source: https://www.marketwatch.com/ Copyright 2020 FactSet Research Systems Inc. All rights reserved. Source FactSet Fundamentals')
        ]),
        dbc.Col([html.Div([
        html.H6('Select Parameter(s) to show trend over the past periods'),
        dcc.Dropdown(
                id='select-column',
                value=['ROCE(%)', 'Sales-to-Capital(%)', 'Net Profit Margin(%)'],
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
                2. TERMINAL_GROWTH_EQ_RISKFREE_RATE = True
                3. No Preferred stock/dividends in capital structure
                4. No Convertible debt/equity portion in capital structure
            '''),
            dbc.Button("Run DCF calculation again with overrides", id='run-dcf', color='primary', block=True)
        ])),
        dbc.Col([
            make_card("Notes/Commentary", "primary",
            dbc.Textarea(bs_size="lg", placeholder='Enter your notes and commentary on the analysis')
            )
        ])
    ],form=True), # row 3
    dbc.Row([
        dbc.Col([
            make_card("DCF table (2-stage Terminal value after 10 years) ", "secondary", 
            dbc.Spinner(html.Div(id="dcf-table")))
        ]),
    ]), # row 4

    dbc.Row([dbc.Col(
        # MD text area Element for interpretation and analysis of data
        dcc.Markdown(children='''
        #### About this App
        - [Inspired by Professor Aswath Damodaran's teachings and Mission](http://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm)
        - [Prof. Damodaran's Data Sources](http://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html)
        - [Prof. Damodaran's Valuation Tools Webcast](https://www.youtube.com/watch?v=F9GfXJ-IrSA)
        - [Prof. Damodaran's Valuation Spreadsheet Download link](http://www.stern.nyu.edu/~adamodar/pc/fcffsimpleginzuCorona.xlsx)
        \n
        *Disclaimer: The Intrinsic Value Calculation here is not as rigorous as the spreadsheet linked above and probably over-simplified in the present version of this app. As it evolves, the App will include more features for completeness over newer releases*\n
        *Assumptions:*\n
        1. Only non-financial companies (neither banks nor insurance companies)
        2. NOLs are not accounted for in DCF valuation (to be improved in future release)
        3. Cost of Capital is fixed for the timeline of valuation and not linked to the Cost of Capital worksheet and the Country Equity Risk Premium look-up (to be improved in future release and linked to source CSV if available)
        4. Probability of failure for the firm assumes proceeds in case of bankruptcy are 50 cents on the $ of Present Value.
        ''')
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
        dbc.Col(make_social_media_share(), align='right', width=400
        )
    ]), # heading row
    html.Div(id='app-2-display-value', children="Under Construction! Please visit later!")
])
