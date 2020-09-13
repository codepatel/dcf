import os
import logging
from pathlib import Path
from time import sleep
import json
import traceback
import pandas as pd
import dash
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# import plotly.graph_objs as go
import plotly.express as px
# from iexfinance.stocks import Stock
# Local imports
# from index import logger
from app import app, cache
from dash_utils import make_table, replace_newline_br_tag
from get_fin_report import get_financial_report, get_number_from_string, get_string_from_number
from get_dcf_valuation import get_dcf_df

# Delete pyc: find . -name \*.pyc -delete

logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                filename=os.path.expandvars('./tmp/app_DCFoutput.log'),
                filemode='w',
                level=logging.INFO)
logger = logging.getLogger()

HERE = Path(__file__).parent
TIMEOUT = 12*60*60  # cache timeout of 12 hours for getting Financial Reported Data update

@cache.memoize(timeout=TIMEOUT*2*30)    # Use Cache Timeout of 30 days for symbols data
def get_symbols():
    with open(Path(HERE, 'assets', 'symbols.json')) as symfile:
        symdata = json.load(symfile)
    return symdata

def ticker_dict():  # For user-entered ticker validation
    return {s['symbol']:s['symbol']+'('+s['exchange']+'):'+s['name'] for s in get_symbols()}

def exchange_list():
    return list(set([s['exchange'] for s in get_symbols()]))

def handler_data_message(title, exception_obj):
    return [{
        'status-info': html.P(children=title, 
        style={'backgroundColor': 'red', 'fontSize': '200%'}),
        'supp-data': html.P(children=str(exception_obj),
        style={'color': 'red'})
        }]

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
            status = c['value'][0]['status-info']   # always 1 element is sent by handler, so use 0
            status_msg.append(status)
            supp = c['value'][0]['supp-data']
            if isinstance(status, str):
                supp_msg.extend(replace_newline_br_tag(supp))
            else:   # it is a dcc or html component, get children
                supp_msg.extend(replace_newline_br_tag(supp['props']['children']))
    return status_msg, supp_msg

@app.callback([Output("ticker-input", "valid"), 
Output("ticker-input", "invalid"),
Output("ticker-allcaps", "children"),
Output('handler-ticker-valid', 'data')],
[Input("ticker-input", "value")])
def check_ticker_validity(ticker):
    try:
        if not ticker:
            raise ValueError("Ticker Value is Empty, please Type Ticker, press Enter or Tab to continue analysis.")
        ticker_allcaps = ticker.upper()
        if ticker.isalpha() and ticker_allcaps in ticker_dict():  # Validate with https://sandbox.iexapis.com/stable/ref-data/symbols?token=
            is_valid_ticker = True
            return is_valid_ticker, not is_valid_ticker, 'Received financial data... for: ' + ticker_allcaps, [{'status-info': ticker_dict()[ticker_allcaps] + ' :\nLast Price ', 
                                                            'supp-data': ''}]
        else:
            raise ValueError("Invalid Ticker entered: " + ticker + '\nValid Tickers from listed Exchanges:\n' + '\n'.join(exchange_list()))
    except Exception as InvalidTicker:
        # dbc.Alert(
        #     str(InvalidTicker),
        #     id="alert-invalid-ticker",
        #     dismissable=True,
        #     is_open=True,
        # )
        logger.exception(InvalidTicker)
        return False, True, '', handler_data_message('See Error Message(s) below:', 
                                                traceback.format_exc())

@cache.memoize(timeout=TIMEOUT)
@app.callback([Output('fin-table', 'children'),
Output('fin-df', 'data'),
Output('select-column', 'options'),
Output('handler-past-data', 'data')],
[Input('ticker-input', 'valid')],
[State('ticker-allcaps', 'children')])
def fin_report(ticker_valid, ticker):
    try:  
        if not ticker_valid:
            raise ValueError("Invalid Ticker entered: " + ticker)
    
        df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker.split(': ')[-1])

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
        return [], [], [], handler_data_message('See Error Message(s) below:', 
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
            raise ValueError("Invalid Data received: " + args[1][0]['supp-data']['props']['children'])
        dcf_df, dcf_output_dict = get_dcf_df(*args)
        dcf_output_df = pd.DataFrame({
                            'Price': [dcf_output_dict['last_price']],
                            'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                            'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])]})
        return make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True), dash.no_update
    except Exception as e:
        logger.exception(e)
        return [], replace_newline_br_tag(traceback.format_exc()), handler_data_message('See Error Message(s) in DCF outputs:', '')
