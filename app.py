from pathlib import Path
import pandas as pd
import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash_table as dt
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
import plotly.express as px
from iexfinance.stocks import Stock

from dash_utils import make_table, make_card, ticker_inputs, make_item, make_social_media_share
from get_fin_report import get_financial_report, get_number_from_string
from get_dcf_valuation import get_dcf_df

# Reference and some Dashboard components inspired by: https://medium.com/swlh/how-to-create-a-dashboard-to-dominate-the-stock-market-using-python-and-dash-c35a12108c93

#instantiate dash app server using flask for easier hosting
server = flask.Flask(__name__)
app = dash.Dash(__name__, server = server, 
    meta_tags=[{ "content": "width=device-width"}], 
    external_stylesheets=[dbc.themes.BOOTSTRAP])
#used for dynamic callbacks
app.config.suppress_callback_exceptions = True


heading_markdown_text = '''
### Purpose of this web app ###
##### To be one of the tools to educate and democratize fundamentals DCF (Discounted Cash Flow) Valuation Analysis of public equity investments #####
See footer below for more on [About this Webapp], Disclaimer and Assumptions
'''

app.layout = html.Div([
    # MD text area Element for interpretation and analysis of data
    dbc.Row([dbc.Col(
        [dcc.Markdown(children=heading_markdown_text)],
        ),
        dbc.Col(make_social_media_share(), align='right', width=400
        )
    ]), # heading row
    dbc.Row([
        dbc.Col([
        make_card("Enter Ticker", "info", ticker_inputs('ticker-input', 'date-picker', 12*5)),
        make_card('Last Price', 'success', html.P(id='last-price', children='Updating...')),
        make_card('MRQ Report date', 'success', html.P(id='mrq-report-date', children='Updating...'))
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
            dbc.Label("Target Pre-Tax Operating Margin (%) in business model (select range: 0 to 30)", html_for="opm-target"),
            dcc.Slider(id="opm-target", min=0, max=30, step=0.1, value=20, 
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
        make_card('DCF Outputs', 'success', html.Div(id="dcf-data"))
        ]),
    ]), #row 1
    # Element for Graph plot of KPIndicators
    dbc.Row([
        dbc.Col([
            make_card("Past records Financial table (Current Year is TTM/MRQ) ", "secondary", 
            html.Div(id="fin-table")),  dt.DataTable(id="fin-df"), dt.DataTable(id="handler-data"), 
            html.Small('Data source: https://www.marketwatch.com/ Copyright 2020 FactSet Research Systems Inc. All rights reserved. Source FactSet Fundamentals')
        ]),
        dbc.Col([
            make_card("DCF table (2-stage Terminal value after 10 years) ", "secondary", 
            html.Div(id="dcf-table"))
        ])
    ]), # row 2
    dbc.Row([
        dbc.Col([html.Div([
        html.H6('Select Parameter(s) to show trend over past period'),
        dcc.Dropdown(
                id='select-column',
                options=[{'label': i, 'value': i} for i in [#'Revenue($)',
                                                            'EPS($)',
                                                            'EPS Growth(%)',
                                                            # 'Pretax Income($)',
                                                            # 'Net Income($)',
                                                            # 'Interest Expense($)',
                                                            # 'EBITDA($)',
                                                            # 'Longterm Debt($)',
                                                            # 'Shareholder Equity($)',
                                                            # 'Total Assets($)',
                                                            # 'Intangible Assets($)',
                                                            # 'Total Current Liabilities($)',
                                                            # 'Capital Expenditures($)',
                                                            'Net Profit Margin',
                                                            'Capital Employed($)',
                                                            'Sales-to-Capital',
                                                            'ROCE',
                                                            'Cash($)',
                                                            'Research & Development($)',
                                                            'Shares Outstanding']],  # list(df.columns)[1:]
                value=['ROCE', 'Sales-to-Capital', 'Net Profit Margin'],
                multi=True
        ),
        dcc.Graph(
            id='plot-indicators'
        )])
    ]),
        dbc.Col(make_card("Intrinsic Value DCF Valuation", "warning", 
        dcc.Markdown(children='''
        ##### Notes/Commentary #####
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
        )
    ], id='cards'), # row 3
    dbc.Row([dbc.Col(
        dcc.Markdown(children='''
        #### About this Webapp ####
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

@app.callback([Output("ticker-input", "valid"), 
Output("ticker-input", "invalid")],
[Input("ticker-input", "value")])
def check_validity(ticker):
    if ticker:
        is_valid_ticker = ticker.isalpha()  
        # TODO: Validate with https://sandbox.iexapis.com/stable/ref-data/symbols?token=
        return is_valid_ticker, not is_valid_ticker
    return False, True

@app.callback([Output('last-price', 'children'),
Output('mrq-report-date', 'children')], 
[Input('ticker-input', 'value'),
Input('handler-data', 'data')])
def refresh_for_update(ticker, handler_list):
    ctx = dash.callback_context
    if not ctx.triggered:
        return tuple(["Enter Ticker to continue"] * 2)
    return handler_list[0]['last-price'], handler_list[0]['mrq-report-data']

@app.callback([Output('fin-table', 'children'),
Output('fin-df', 'data'),
Output('handler-data', 'data')], 
[Input('ticker-input', 'value'),
Input('ticker-input', 'valid')])
def fin_report(ticker, ticker_validity):
    if not ticker:
        raise ValueError("Ticker Value is Empty, please Type Ticker, press Enter or Tab to continue analysis.")
    if not ticker_validity:
        raise ValueError("Invalid Ticker entered: " + ticker)
    ticker = ticker.upper()
    try:
        df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker)
        #table = make_table('table-sorting-filtering3', df, '20px',8)
        table = dbc.Table.from_dataframe(df[['index', 'Revenue($)', 'EPS($)', 'EPS Growth(%)', 
                'Pretax Income($)', 'Shareholder Equity($)', 'Longterm Debt($)', 'Capital Expenditures($)']], 
                striped=True, bordered=True, hover=True)
        handler_data = {'last-price': lastprice + ' @ ' + lastprice_time, 
                        'mrq-report-data': report_date_note}
        return table, df.to_dict('records'), [handler_data]
        # 'records' is more "compatible" than 'series'
    except ValueError as InvalidTicker:
        dbc.Alert(
            str(InvalidTicker),
            id="alert-invalid-ticker",
            dismissable=True,
            is_open=True,
        )
        raise

@app.callback(Output('plot-indicators', 'figure'),
[Input('select-column', 'value'),
Input('fin-df', 'data')])
def update_graph(column_name, df_dict):
    df = pd.DataFrame.from_dict(df_dict).applymap(get_number_from_string)
    fig = px.line(df, x='index', y=column_name,
                    line_shape='spline')
    fig.update_traces(mode='lines+markers')
    fig.update_layout(
        title="Past Performance is not a guarantee of Future Returns",
        xaxis_title="Year",
        yaxis_title="Value ($ or Ratio or %)",
        legend_title="Parameter(s)"
    )
    return fig

@app.callback([Output('dcf-table', 'children'),
Output('dcf-data', 'children')],
[Input('fin-df', 'data'),
Input('handler-data', 'data'),
Input('rgr-next', 'value'),
Input('opm-next', 'value'),
Input('cagr-2-5', 'value'),
Input('opm-target', 'value'),
Input('sales-to-cap', 'value'),
Input('tax-rate', 'value'),
Input('riskfree-rate', 'value'),
Input('cost-of-cap', 'value'),
])
def dcf_valuation(*args, **kwargs):
    dcf_df, dcf_output_dict = get_dcf_df(*args)
    dcf_output_df = pd.DataFrame({
                        'Price': [dcf_output_dict['last_price']],
                        'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                        'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])]})
    return make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True)

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter
