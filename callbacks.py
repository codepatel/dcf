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
from __init__ import logger, HERE, TIMEOUT_12HR
from app import app, cache
from dash_utils import make_table, replace_str_element_w_dash_component
from get_fin_report import get_financial_report, get_yahoo_fin_values, get_number_from_string, get_string_from_number
from get_dcf_valuation import get_dcf_df

# Delete pyc: find . -name \*.pyc -delete

@cache.memoize(timeout=TIMEOUT_12HR*2*30)    # Use Cache Timeout of 30 days for symbols data
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
                supp_msg.extend(replace_str_element_w_dash_component(supp, repl_dash_component=[]))
            else:   # it is a dcc or html component, get children
                supp_msg.extend(replace_str_element_w_dash_component(supp['props']['children']))
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
            return is_valid_ticker, not is_valid_ticker, 'Getting financial data... for: ' + ticker_allcaps, [{'status-info': ticker_dict()[ticker_allcaps] + ' :\nLast Price ', 
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

@app.callback([Output('fin-table', 'children'),
Output('fin-df', 'data'),
Output('select-column', 'options'),
Output('handler-past-data', 'data')],
[Input('ticker-input', 'valid')],
[State('ticker-allcaps', 'children')])
def fin_report(ticker_valid, ticker): 
    if not ticker_valid:
        return [], [], [], dash.no_update
    try:
        ticker_allcaps = ticker.split(': ')[-1]
        df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker_allcaps)
        next_earnings_date, beta = get_yahoo_fin_values(ticker_allcaps)

        table = dbc.Table.from_dataframe(df[['index', 'Revenue($)', 'EPS($)', 'EPS Growth(%)', 
                'Pretax Income($)', 'Shareholder Equity($)', 'Longterm Debt($)', 'Capital Expenditures($)']], 
                striped=True, bordered=True, hover=True)
        supp_data_notes = f'MRQ report ending: {report_date_note},\n' \
            f"Shares outstanding: {df['Shares Outstanding'].iloc[-1]},\n" \
            f"Market Cap: {get_string_from_number(get_number_from_string(df['Shares Outstanding'].iloc[-1]) * float(lastprice.replace(',','')))},\n" \
            f"Cash as of MRQ: {df['Cash($)'].iloc[-1]},\n" \
            f"Beta: {beta},\n" \
            f"Next Earnings date: {next_earnings_date},\n"
            
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
    if not df_dict:
        return {}
    try:
        df = pd.DataFrame.from_dict(df_dict)
        df = pd.concat([df.iloc[:,0], df.iloc[:,1:].applymap(get_number_from_string)], axis=1)
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
Input('run-dcf', 'n_clicks'),
Input('year0-revenue', 'value'),
Input('year0-randd', 'value'),
Input('year0-capex', 'value'),
Input('year0-ebit', 'value'),
Input('year0-rgr', 'value'),
Input('minority-interests', 'value'),
Input('nonoperating-assets', 'value'),
Input('options-value', 'value')],
[State('convergence-year', 'value'),
State('marginal-tax', 'value'),
State('prob-failure', 'value'),])
def dcf_valuation(*args, **kwargs):    
    if not args[0]:
        return [], [], dash.no_update
    try:
        dcf_df, dcf_output_dict = get_dcf_df(*args)
        dcf_output_df = pd.DataFrame({
                            'Price': [dcf_output_dict['last_price']],
                            'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                            'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])]})
        return make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True), dash.no_update
    except TypeError as e:
        logger.exception(e)
        return [], replace_str_element_w_dash_component(traceback.format_exc()), handler_data_message('See Error Message(s) in DCF outputs:', '')
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate
        
