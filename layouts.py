import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
# Local imports
from dash_utils import make_card, ticker_inputs, make_item, make_social_media_share

# Reference and some Dashboard components inspired by: https://medium.com/swlh/how-to-create-a-dashboard-to-dominate-the-stock-market-using-python-and-dash-c35a12108c93

navheader = dbc.Nav([
        dbc.NavLink("DCF Valuation Analysis", href="/apps/dcf"),
        dbc.NavLink("Sector Value Analysis", href="/apps/sector")
    ])

dcflayout = html.Div([
    html.H3('DCF Valuation Analysis'),
    navheader,
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
        make_card('DCF Inputs - Company factors', 'info', dbc.Form([
            dbc.Label("Revenue Growth Rate (%) for next year (select range: -50 to 50)", html_for="rgr-next"),
            dcc.Slider(id="rgr-next", min=-40, max=20, step=0.1, value=0, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Operating Margin (%) for next year (select range: -10 to 30)", html_for="opm-next"),
            dcc.Slider(id="opm-next", min=-10, max=30, step=0.1, value=10, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("CAGR (%) for years 2-5 (select range: 0 to 15)", html_for="cagr-2-5"),
            dcc.Slider(id="cagr-2-5", min=0, max=15, step=0.1, value=5, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Target Pre-Tax Operating Margin (%) in business model (select range: 0 to 50)", html_for="opm-target"),
            dcc.Slider(id="opm-target", min=0, max=50, step=0.1, value=20, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Sales to capital ratio (for computing reinvestment, select range: 0 to 4)", html_for="sales-to-cap"),
            dcc.Slider(id="sales-to-cap", min=0, max=4, step=0.05, value=1, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
        ]))]),
        dbc.Col([
        make_card('DCF Inputs - Environmental factors', 'info', dbc.Form([
            dbc.Label("Effective Tax Rate (%) (select range: 0 to 30)", html_for="tax-rate"),
            dcc.Slider(id="tax-rate", min=0, max=30, step=0.1, value=15, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Riskfree Rate (%) (select range: 0 to 5)", html_for="riskfree-rate"),
            dcc.Slider(id="riskfree-rate", min=0, max=5, step=0.25, value=3.5, 
            tooltip={'always_visible': True, 'placement': 'topRight'}),
            dbc.Label("Cost of Capital (%) (select range: 0 to 12)", html_for="cost-of-cap"),
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
            dbc.Spinner(html.Div(id="fin-table"))),  dt.DataTable(id="fin-df"), 
                dt.DataTable(id="handler-ticker-valid"),
                dt.DataTable(id="handler-past-data"), 
                dt.DataTable(id="handler-dcf-data"),
            html.Small('Data source: https://www.marketwatch.com/ Copyright 2020 FactSet Research Systems Inc. All rights reserved. Source FactSet Fundamentals')
        ]),
        dbc.Col([html.Div([
        html.H6('Select Parameter(s) to show trend over the past periods'),
        dcc.Dropdown(
                id='select-column',
                value=['ROCE', 'Sales-to-Capital', 'Net Profit Margin'],
                multi=True
        ),
        dbc.Spinner(dcc.Graph(
            id='plot-indicators'
        ))])
        ]),
        
    ]), # row 2
    dbc.Row([
        dbc.Col(make_card("Intrinsic Value DCF Valuation", "warning", 
        dcc.Markdown(children='''
        **Assumptions for DCF:**\n
            1. TERMINAL_YEAR_LENGTH = 10
            2. TERMINAL_GROWTH_EQ_RISKFREE_RATE = True
            3. CONVERGENCE_PERIOD = 3
            4. MARGINAL_TAX_RATE = 0.29
            5. PROBABILITY_OF_FAILURE = 0.05
            6. MINORITY_INTERESTS = 0
            7. NONOPERATING_ASSETS = 0
            8. OPTIONS_VALUE = 0
        '''))
        ),
        dbc.Col([
            make_card("Notes/Commentary", "primary",
            dbc.Textarea(bs_size="lg", placeholder='Enter your notes and commentary on the analysis')
            )
        ])
    ]), # row 3
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
        4. Probability of failure for the firm and Proceeds if so is not considered (yet!)
        5. Employee Options Value Impact is not considered (yet!)
        ''')
        )
    ])  # footer row
])

sectorlayout = html.Div([
    html.H3('Sector Value Analysis'),
    navheader,
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
