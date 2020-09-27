from pathlib import Path
from time import sleep
import json
import traceback
import uuid
import pandas as pd
import dash
# from dash.dependencies import Input, Output, State
from dash_extensions.enrich import Output, Input, Trigger, ServersideOutput, State
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# import plotly.graph_objs as go
import plotly.express as px
# from iexfinance.stocks import Stock
# Local imports
from __init__ import logger, HERE, TIMEOUT_12HR, DEFAULT_TICKER
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

@app.callback([Output('ticker-input', 'value'),
Output('analysis-mode', 'value'),
Output('snapshot-uuid', 'value'),
Output('handler-parseURL', 'data')],
[Input('nav-dcf', 'active')],
[Input('url', 'pathname')])
def parse_ticker(dcf_app_active, pathname):
    if dcf_app_active:
        parse_ticker = pathname.split('/apps/dcf')[-1].split('/')
        if len(parse_ticker) == 1:
            return DEFAULT_TICKER, [1], str(uuid.uuid5(uuid.uuid4(), DEFAULT_TICKER)), dash.no_update
        elif len(parse_ticker) == 2:
            ticker_value = parse_ticker[1].upper() or DEFAULT_TICKER
            return ticker_value, [1], str(uuid.uuid5(uuid.uuid4(), ticker_value)), dash.no_update
        else:   # >=3
            if parse_ticker[2]:
                try:
                    uuid_val = uuid.UUID(parse_ticker[2], version=5)
                    if uuid_val.hex == parse_ticker[2].replace('-',''):
                        return parse_ticker[1].upper() or DEFAULT_TICKER, [], parse_ticker[2], dash.no_update
                    else:
                        raise ValueError("Bad Snapshot ID from URL: " + parse_ticker[2])
                except:
                    return parse_ticker[1].upper() or DEFAULT_TICKER, [], '', handler_data_message('See Error Message(s) below:', traceback.format_exc())

            else:
                return parse_ticker[1].upper(), [], str(uuid.uuid5(uuid.uuid4(), parse_ticker[1].upper())), dash.no_update
    else:
        raise PreventUpdate

@app.callback([Output('snapshot-link', 'href'),
Output('save-snapshot', 'disabled'),
Output('snapshot-link', 'disabled')],
[Input('analysis-mode', 'value'),
Input('save-snapshot', 'n_clicks'),
Input('ticker-input', 'value'),
Input('snapshot-uuid', 'value')])
def save_snapshot(live_analysis_mode, save_button_clicked, ticker, snapshot_uuid):
    if 1 in live_analysis_mode: # generate a fresh UUID
        snapshot_uuid = str(uuid.uuid5(uuid.UUID(snapshot_uuid), ticker))
        return '/apps/dcf/' + ticker + '/' + snapshot_uuid, False, not save_button_clicked
    else:
        return dash.no_update, True, True

@app.callback([Output('status-info', 'children'),
Output('supp-info', 'children')], 
[Input('handler-parseURL', 'data'),
Input('handler-ticker-valid', 'data'),
Input('handler-past-data', 'data'),
Input('handler-dcf-data', 'data'),
Input('status-info', 'loading_state')])
def refresh_for_update(handler_parseURL, handler_ticker, handler_past, handler_dcf, status_loading_dict):
    ctx = dash.callback_context
    if not ctx.triggered:
        return tuple(["Enter Ticker to continue"] * 2)
    status_msg = []
    supp_msg = []
    triggered_elements = [c['prop_id'] for c in ctx.triggered]
    if 'handler-ticker-valid.data' in triggered_elements and ctx.inputs['status-info.loading_state']['is_loading']:
        return ctx.inputs['handler-ticker-valid.data'][0]['status-info'], ctx.inputs['handler-ticker-valid.data'][0]['supp-data']
        # return 'Updating...', 'Updating...'
    else:
        update_data = [d for c, d in ctx.inputs.items() if '.data' in c]
        for d in update_data:
            if d:
                status = d[0]['status-info']   # always 1 element is sent by handler, so use 0
                status_msg.append(status)
                supp = d[0]['supp-data']
                if isinstance(supp, str):
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
        if ticker_allcaps in ticker_dict():  # Validate with https://sandbox.iexapis.com/stable/ref-data/symbols?token=
            is_valid_ticker = True
            return is_valid_ticker, not is_valid_ticker, 'Getting financial data... for: ' + ticker_dict()[ticker_allcaps], [{'status-info': 'Last Price ', 
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

@app.callback([ServersideOutput('fin-store', 'data'),
Output('select-column', 'options'),
Output('status-info', 'loading_state'),
Output('handler-past-data', 'data')],
[Input('ticker-input', 'valid')],
[State('ticker-input', 'value'),
State('analysis-mode', 'value')])
def fin_report(ticker_valid, ticker, live_analysis_mode): 
    if not ticker_valid:
        return [], [], {'is_loading': True}, dash.no_update
    try:
        ticker_allcaps = ticker.upper()
        if 1 in live_analysis_mode:
            df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker_allcaps)
            next_earnings_date, beta = get_yahoo_fin_values(ticker_allcaps)

            stats_record = {'ticker': ticker_allcaps,
                            'lastprice': float(lastprice.replace(',','')),
                            'lastpricetime': lastprice_time,
                            'beta': beta,
                            'next_earnings_date': next_earnings_date
                            }

            supp_data_notes = f'MRQ report ending: {report_date_note},\n' \
                f"Shares outstanding: {df['Shares Outstanding'].iloc[-1]},\n" \
                f"Market Cap: {get_string_from_number(get_number_from_string(df['Shares Outstanding'].iloc[-1]) * stats_record['lastprice'])},\n" \
                f"Cash as of MRQ: {df['Cash($)'].iloc[-1]},\n" \
                f"Beta: {beta},\n" \
                f"Next Earnings date: {next_earnings_date},\n"

            handler_data = {'status-info': lastprice + ' @ ' + lastprice_time, 
                            'supp-data': supp_data_notes}
            select_column_options = [{'label': i, 'value': i} for i in list(df.columns)[1:]]

            return {ticker_allcaps: {'fin_report_dict': df.to_dict('records'), 'stats_dict': stats_record}}, select_column_options, {'is_loading': False}, [handler_data]
            # 'records' is more "compatible" than 'series'
        else:
            raise PreventUpdate     # pull output callback from from server cache or database
    except Exception as e:       
        logger.exception(e)
        return [], [], {'is_loading': False}, handler_data_message('See Error Message(s) below:', 
                                                                traceback.format_exc())

@app.callback(Output('fin-table', 'children'),
Input('fin-store', 'data'),
State('ticker-input', 'value'))
def update_historical_table(df_dict, ticker):
    if not df_dict:
        return []
    try:
        return dbc.Table.from_dataframe(pd.DataFrame.from_dict(df_dict[ticker]['fin_report_dict'])[['index', 'Revenue($)', 'EPS($)', 'EPS Growth(%)', 
              'Pretax Income($)', 'Shareholder Equity($)', 'Longterm Debt($)', 'Net Investing Cash Flow($)']], 
              striped=True, bordered=True, hover=True)
    except Exception as e:
        logger.exception(e)
        return []


@app.callback(Output('plot-indicators', 'figure'),
[Input('fin-store', 'data'),
Input('select-column', 'value')],
State('ticker-input', 'value'))
def update_graph(df_dict, column_name, ticker):
    if not df_dict:
        return {}
    try:
        df_str_format = pd.DataFrame.from_dict(df_dict[ticker]['fin_report_dict'])
        df = pd.concat([df_str_format.iloc[:,0], df_str_format.iloc[:,1:].applymap(get_number_from_string)], axis=1)
        for col in list(df.columns):
            if '%' in col:  # scale up ratio by 100 if unit is %
                df[col] = df[col]*100
        fig = px.line(df, x='index', y=column_name,
                        line_shape='spline')
        fig.update_traces(mode='lines+markers')
        fig.update_layout(
            title=ticker + ": Past Performance is not a guarantee of Future Returns",
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
[Input('fin-store', 'data'),
Input('rgr-next', 'value'),
Input('opm-next', 'value'),
Input('cagr-2-5', 'value'),
Input('opm-target', 'value'),
Input('sales-to-cap', 'value'),
Input('tax-rate', 'value'),
Input('riskfree-rate', 'value'),
Input('terminal-growth-rate', 'value'),
Input('cost-of-cap', 'value'),
Input('run-dcf', 'n_clicks'),
Input('year0-revenue', 'value'),
Input('year0-randd', 'value'),
Input('year0-capex', 'value'),
Input('year0-ebit', 'value'),
Input('year0-rgr', 'value'),
Input('cash', 'value'),
Input('debt-book-value', 'value'),
Input('shares-outstanding', 'value'),
Input('minority-interests', 'value'),
Input('nonoperating-assets', 'value'),
Input('options-value', 'value')],
[State('convergence-year', 'value'),
State('marginal-tax', 'value'),
State('prob-failure', 'value'),
State('terminal-growth-rate', 'disabled'),])
def dcf_valuation(*args, **kwargs):    
    if not args[0]:
        return [], [], dash.no_update
    try:
        dcf_df, dcf_output_dict = get_dcf_df(*args)
        dcf_output_df = pd.DataFrame({
                            'Price': [dcf_output_dict['last_price']],
                            'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                            'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])],
                            'PV Total': [get_string_from_number(dcf_output_dict['PV_sum'])],
                            'PV Terminal Value': [get_string_from_number(dcf_output_dict['PV_terminal_value'])],
                            })
        return make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True), dash.no_update
    except TypeError as e:
        logger.exception(e)
        return [], replace_str_element_w_dash_component(traceback.format_exc()), handler_data_message('See Error Message(s) in DCF outputs:', '')
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate
        
