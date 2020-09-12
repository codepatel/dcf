import os
import traceback
import json
from pathlib import Path
import logging
import pandas as pd
import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash_table as dt
from dash.exceptions import PreventUpdate
# import plotly.graph_objs as go
import plotly.express as px
# from iexfinance.stocks import Stock

from dash_utils import make_table, make_card, ticker_inputs, make_item, make_social_media_share
from get_fin_report import get_financial_report, get_number_from_string, get_string_from_number
from get_dcf_valuation import get_dcf_df

HERE = Path(__file__).parent

if not os.path.exists('tmp'):
    os.makedirs('tmp')

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./tmp/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()

# Reference and some Dashboard components inspired by: https://medium.com/swlh/how-to-create-a-dashboard-to-dominate-the-stock-market-using-python-and-dash-c35a12108c93

#instantiate dash app server using flask for easier hosting
server = flask.Flask(__name__)
app = dash.Dash(__name__, server = server, 
    meta_tags=[{ "content": "width=device-width"}], 
    external_stylesheets=[dbc.themes.BOOTSTRAP])
#used for dynamic callbacks
app.config.suppress_callback_exceptions = True

with open(Path(HERE, 'assets', 'symbols.json')) as symfile:
    symdata = json.load(symfile)
ticker_dict = {s['symbol']:s['symbol']+'('+s['exchange']+'):'+s['name'] for s in symdata}

heading_markdown_text = '''
### Purpose of this web app ###
##### To be one of the tools to educate and democratize fundamentals DCF (Discounted Cash Flow) Valuation Analysis of public equity investments #####
See footer below for more on [About this DCF Valuation App](#about-this-app), Disclaimer and Assumptions
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
        make_card("Enter Ticker", "info", ticker_inputs('ticker-input', 'date-picker', 12*5)
        # dbc.Select(
        #     id='ticker-input', 
        #     options=[{'label': s['symbol']+'('+s['exchange']+'):'+s['name'], 'value': s['symbol']} for s in symdata],
        #     value='AAPL',
        #     placeholder='Start typing Ticker, press Enter')
        ),
        make_card('Status Message', 'success', html.P(id='status-info', children='Updating...')),
        make_card('Supplemental Info', 'success', html.P(id='supp-info', children='Updating...'))
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
        make_card('DCF Outputs', 'success', html.Div(id="dcf-data"))
        ]),
    ]), #row 1
    # Element for Graph plot of KPIndicators
    dbc.Row([
        dbc.Col([
            make_card("Past records Financial table (Current Year is TTM/MRQ) ", "secondary", 
            html.Div(id="fin-table")),  dt.DataTable(id="fin-df"), 
                dt.DataTable(id="handler-ticker-valid"),
                dt.DataTable(id="handler-past-data"), 
                dt.DataTable(id="handler-dcf-data"),
            html.Small('Data source: https://www.marketwatch.com/ Copyright 2020 FactSet Research Systems Inc. All rights reserved. Source FactSet Fundamentals')
        ]),
        dbc.Col([
            make_card("DCF table (2-stage Terminal value after 10 years) ", "secondary", 
            html.Div(id="dcf-table"))
        ])
    ]), # row 2
    dbc.Row([
        dbc.Col([html.Div([
        html.H6('Select Parameter(s) to show trend over the past periods'),
        dcc.Dropdown(
                id='select-column',
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

def handler_data_message(title, exception_obj):
    return [{
        'status-info': html.P(children=title, 
        style={'backgroundColor': 'red', 'fontSize': '200%'}),
        'supp-data': html.P(children=str(exception_obj),
        style={'color': 'red'})
        }]

@app.callback([Output("ticker-input", "valid"), 
Output("ticker-input", "invalid"),
Output('handler-ticker-valid', 'data')],
[Input("ticker-input", "value")])
def check_ticker_validity(ticker):
    try:
        if not ticker:
            raise ValueError("Ticker Value is Empty, please Type Ticker, press Enter or Tab to continue analysis.")
        if ticker.isalpha() and ticker.upper() in ticker_dict:  # Validate with https://sandbox.iexapis.com/stable/ref-data/symbols?token=
            is_valid_ticker = True
            return is_valid_ticker, not is_valid_ticker, [{'status-info': 'Received financial data... for ' + ticker_dict[ticker.upper()] + ' :\nLast Price ', 
                                                            'supp-data': ''}]
        else:
            raise ValueError("Invalid Ticker entered: " + ticker)
    except Exception as InvalidTicker:
        # dbc.Alert(
        #     str(InvalidTicker),
        #     id="alert-invalid-ticker",
        #     dismissable=True,
        #     is_open=True,
        # )
        logger.exception(InvalidTicker)
        return False, True, handler_data_message('See Error Message below:', 
                                                traceback.format_exc())

@app.callback([Output('status-info', 'children'),
Output('supp-info', 'children')], 
[Input('handler-ticker-valid', 'data'),
Input('handler-past-data', 'data'),
Input('handler-dcf-data', 'data')])
def refresh_for_update(handler_ticker, handler_past, handler_dcf):
    ctx = dash.callback_context
    if not ctx.triggered:
        return tuple(["Enter Ticker to continue"] * 2)
    status_msg = []
    supp_msg = []
    for c in ctx.triggered:
        if c['value']:
            status_msg.append(c['value'][0]['status-info'])
            supp_msg.append(c['value'][0]['supp-data'])
    return status_msg, supp_msg

@app.callback([Output('fin-table', 'children'),
Output('fin-df', 'data'),
Output('select-column', 'options'),
Output('handler-past-data', 'data')],
[Input('ticker-input', 'valid')],
[State('ticker-input', 'value')])
def fin_report(ticker_valid, ticker):
    try:  
        if not ticker_valid:
            raise ValueError("Invalid Ticker entered: " + ticker)
        
        ticker = ticker.upper()
    
        df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker)
        #table = make_table('table-sorting-filtering3', df, '20px',8)
        table = dbc.Table.from_dataframe(df[['index', 'Revenue($)', 'EPS($)', 'EPS Growth(%)', 
                'Pretax Income($)', 'Shareholder Equity($)', 'Longterm Debt($)', 'Capital Expenditures($)']], 
                striped=True, bordered=True, hover=True)
        supp_data_notes = f'MRQ report ending: {report_date_note}, ' \
            f"Shares outstanding: {df['Shares Outstanding'].iloc[-1]}, " \
            f"Market Cap: {get_string_from_number(get_number_from_string(df['Shares Outstanding'].iloc[-1]) * float(lastprice.replace(',','')))}, " \
            f"Cash as of MRQ: {df['Cash($)'].iloc[-1]}"
        handler_data = {'status-info': lastprice + ' @ ' + lastprice_time, 
                        'supp-data': supp_data_notes}
        select_column_options = [{'label': i, 'value': i} for i in list(df.columns)[1:]]

        return table, df.to_dict('records'), select_column_options, [handler_data]
        # 'records' is more "compatible" than 'series'
    except Exception as e:       
        logger.exception(e)
        return [], [], [], handler_data_message('See Error Message below:', 
                                                traceback.format_exc())

@app.callback(Output('plot-indicators', 'figure'),
[Input('select-column', 'value'),
Input('fin-df', 'data')])
def update_graph(column_name, df_dict):
    try:
        df = pd.DataFrame.from_dict(df_dict).applymap(get_number_from_string)
        for col in list(df.columns):
            if '%' in col:  # scale up ratio by 100 if unit is %
                df[col] = df[col]*100
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
    except Exception as e:
        logger.exception(e)
        return {}

@app.callback([Output('dcf-table', 'children'),
Output('dcf-data', 'children'),
Output('handler-dcf-data', 'data')],
[Input('fin-df', 'data'),
Input('handler-past-data', 'data'),
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
    try:
        if not args[0]:
            raise ValueError("Invalid Data received: " + args[1]['supp-data'])
        dcf_df, dcf_output_dict = get_dcf_df(*args)
        dcf_output_df = pd.DataFrame({
                            'Price': [dcf_output_dict['last_price']],
                            'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                            'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])]})
        return make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True), []
    except Exception as e:
        logger.exception(e)
        return [],[], handler_data_message('See Error Message below:', 
                                                traceback.format_exc())

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter
