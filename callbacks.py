import os
from pathlib import Path
import time
import json
import traceback
import uuid
import pandas as pd
import dash
from dash.dependencies import Input, Output, State
from dash_extensions.enrich import ServersideOutput
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# import plotly.graph_objs as go
import plotly.express as px
import requests
import asyncio
from sseclient import SSEClient
# from iexfinance.stocks import Stock
# Local imports
from __init__ import HERE, TIMEOUT_12HR, DEFAULT_TICKER, DEFAULT_SNAPSHOT_UUID, ticker_dict, exchange_list
from app import app, cache, db, logger
from dash_utils import make_table, replace_str_element_w_dash_component
from get_fin_report import get_financial_report, get_yahoo_fin_values, get_number_from_string, get_string_from_number, get_sector_data
from get_dcf_valuation import get_dcf_df

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
[Input('nav-dcf', 'active'),
Input('url', 'pathname')])
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
Input('snapshot-uuid', 'value')],
State('dcf-store', 'data'))
def save_snapshot(live_analysis_mode, save_button_clicked, ticker, snapshot_uuid, df_dict):
    if 1 in live_analysis_mode: # generate a fresh UUID
        snapshot_uuid = str(uuid.uuid5(uuid.UUID(snapshot_uuid), ticker))
        if save_button_clicked:
            # df_dict[ticker] = {**df_dict[ticker], **dcf_dict[ticker]}
            db.set(ticker+'-'+snapshot_uuid, json.dumps(df_dict))
        return '/apps/dcf/' + ticker + '/' + snapshot_uuid, False, not save_button_clicked
    else:
        return dash.no_update, True, True

@app.callback([Output('status-info', 'children'),
Output('supp-info', 'children')], 
[Input('handler-parseURL', 'data'),
Input('handler-ticker-valid', 'data'),
Input('handler-past-data', 'data'),
Input('handler-dcf-data', 'data'),
Input('handler-lastpricestream', 'data'),
Input('status-info', 'loading_state')])
def refresh_for_update(handler_parseURL, handler_ticker, handler_past, handler_dcf, handler_lastpricestream, status_loading_dict):
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
                status_msg += status
                supp = d[0]['supp-data']
                if isinstance(supp, str):
                    supp_msg.extend(replace_str_element_w_dash_component(supp, repl_dash_component=[]))
                elif supp:   # it is a dcc or html component, get children
                    supp_msg.extend(replace_str_element_w_dash_component(supp['props']['children']))
        return status_msg, supp_msg or dash.no_update

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
            return is_valid_ticker, not is_valid_ticker, 'Getting financial data... for: ' + ticker_dict()[ticker_allcaps], [{'status-info': 'Market Price used in Calculation: ', 
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
State('analysis-mode', 'value'),
State('snapshot-uuid', 'value')])
def fin_report(ticker_valid, ticker, live_analysis_mode, snapshot_uuid): 
    if not ticker_valid:
        return [], [], {'is_loading': True}, dash.no_update
    try:
        ticker_allcaps = ticker.upper()
        db_key = ticker_allcaps+'-'+snapshot_uuid
        if 1 in live_analysis_mode or not db.exists(db_key):
            df, lastprice, lastprice_time, report_date_note = get_financial_report(ticker_allcaps)
            next_earnings_date, beta = get_yahoo_fin_values(ticker_allcaps)

            stats_record = {'ticker': ticker_allcaps,
                            'lastprice': float(lastprice.replace(',','')),
                            'lastprice_time': lastprice_time,
                            'beta': beta,
                            'next_earnings_date': next_earnings_date,
                            'report_date_note': report_date_note
                            }

            df_dict = {ticker_allcaps: {'fin_report_dict': df.to_dict('records'), 'stats_dict': stats_record}}
        else:
            df_dict = json.loads(db.get(db_key))  # pull output callback from from server cache or database: redis
            if not df_dict:
                raise KeyError('Redis Key not found: ' + db_key + '\nPlease click the app tab link to refresh state!')
            df = pd.DataFrame.from_dict(df_dict[ticker_allcaps]['fin_report_dict'])
            stats_record = df_dict[ticker_allcaps]['stats_dict']
        select_column_options = [{'label': i, 'value': i} for i in list(df.columns)[1:]]

        supp_data_notes = f"MRQ report ending: {stats_record['report_date_note']},\n" \
            f"Shares outstanding: {df['Shares Outstanding'].iloc[-1]},\n" \
            f"Market Cap: {get_string_from_number(get_number_from_string(df['Shares Outstanding'].iloc[-1]) * stats_record['lastprice'])},\n" \
            f"Cash as of MRQ: {df['Cash($)'].iloc[-1]},\n" \
            f"Beta: {stats_record['beta']},\n" \
            f"Next Earnings date: {stats_record['next_earnings_date']},\n"
        handler_data = {'status-info': f"{stats_record['lastprice']}", 
                        'supp-data': supp_data_notes}
        
        return df_dict, select_column_options, {'is_loading': False}, [handler_data]
        # 'records' is more "compatible" than 'series'        
    except Exception as e:       
        logger.exception(e)
        return [], [], {'is_loading': False}, handler_data_message('See Error Message(s) below:', traceback.format_exc())

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
                df.loc[:, col] *= 100
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

@app.callback([ServersideOutput('dcf-store', 'data'),
Output('dcf-table', 'children'),
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
State('terminal-growth-rate', 'disabled'),
State('analysis-mode', 'value'),
State('snapshot-uuid', 'value')])
def dcf_valuation(*args, **kwargs):    
    if not args[0]:
        return [], [], [], dash.no_update
    try:
        df_dict = args[0]
        live_analysis_mode = args[-2]
        snapshot_uuid = args[-1]
        ticker = list(df_dict.keys())[0]
        dcf_store_dict_json = db.get(ticker+'-'+snapshot_uuid)
        dcf_store_dict = json.loads(dcf_store_dict_json) if dcf_store_dict_json else None
        safe_get_dcf = dcf_store_dict.get(ticker).get('dcf_df_dict') if dcf_store_dict else None
        if 1 in live_analysis_mode or not safe_get_dcf:
            dcf_df, dcf_output_dict = get_dcf_df(*args)
        else:
            dcf_df = pd.DataFrame.from_dict(safe_get_dcf)
            dcf_output_dict = dcf_store_dict[ticker]['dcf_output_dict']
        # Capture all inputs to dcf-store.data
        ctx = dash.callback_context
        dcf_store_dict = ctx.inputs.pop('fin-store.data')
        for k, v in ctx.inputs.items():
            dcf_store_dict[ticker][k] = v
        dcf_store_dict[ticker]['dcf_df_dict'] = dcf_df.to_dict('records')
        dcf_store_dict[ticker]['dcf_output_dict'] = dcf_output_dict
        
        dcf_output_df = pd.DataFrame({
                            'Price': [dcf_output_dict['last_price']],
                            'Value': ['{:.2f}'.format(dcf_output_dict['estimated_value_per_share'])],
                            'Price as % of Value': ['{:.2f}'.format(100*dcf_output_dict['last_price']/dcf_output_dict['estimated_value_per_share'])],
                            'PV Total': [get_string_from_number(dcf_output_dict['PV_sum'])],
                            'PV Terminal Value': [get_string_from_number(dcf_output_dict['PV_terminal_value'])],
                            })
        return dcf_store_dict, make_table('dcf-df', dcf_df), dbc.Table.from_dataframe(dcf_output_df, striped=True, bordered=True, hover=True), dash.no_update
    except TypeError as e:
        logger.exception(e)
        return [], [], replace_str_element_w_dash_component(traceback.format_exc()), handler_data_message('See Error Message(s) in DCF outputs:', '')
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate
        
@app.callback([ServersideOutput('sector-store', 'data'),
Output('crossfilter-xaxis-column', 'options'),
Output('crossfilter-yaxis-column', 'options'),
Output('select-company', 'options')],
[Input('select-sector', 'value')],
)
def update_sector_analysis(sector_names):
    if not sector_names:
        return {}, [], [], []
    try:
        sector_dict = {}
        for s in sector_names:
            sector_data = get_sector_data(s)
            for ticker in sector_data:
                sector_data[ticker]['advanced-stats']['sector'] = s
            sector_dict.update(sector_data)
        sector_df = pd.DataFrame.from_dict({s:sector_dict[s]['advanced-stats'] for s in sector_dict}, orient='index')
        xfilter_options = [{'label': i, 'value': i} for i in list(sector_df.columns) + ['EBITDAToEV(%)', 'EBITDAToRevenueMargin', 'TotalAssets', 'EBITDAToAssets(%)']]
        company_options = [{'label': c, 'value': c} for c in list(sector_df.companyName)]
        return sector_dict, xfilter_options, xfilter_options, company_options
    except Exception as e:
        logger.exception(e)
        return {}, [], [], []

@app.callback([Output('sector-distribution', 'figure')],
[Input('sector-store', 'data'),
Input('select-company', 'value'),
Input('sector-ev-filter', 'value'),
Input('crossfilter-xaxis-column', 'value'),
Input('crossfilter-yaxis-column', 'value')],
)
def graph_sector_matrix(sector_dict, company_selections, ev_limits, xaxis, yaxis):
    if not sector_dict:
        return []
    sector_df = pd.DataFrame.from_dict({s:sector_dict[s]['advanced-stats'] for s in sector_dict}, orient='index')
    if not company_selections:
        sector_df_filtered = sector_df.query(f"enterpriseValue >= {10 ** ev_limits[0]} \
                        & enterpriseValue <= {10 ** ev_limits[1]}")
    else:
        sector_df_filtered = sector_df.query(f"companyName in {company_selections} \
                        & enterpriseValue >= {10 ** ev_limits[0]} \
                        & enterpriseValue <= {10 ** ev_limits[1]}")
    total_companies = len(sector_df_filtered)
    if not total_companies:
        return []
    else:
        sector_df_filtered.loc[:, 'EBITDAToEV(%)'] = sector_df_filtered.EBITDA / sector_df_filtered.enterpriseValue
        sector_df_filtered.loc[:, 'EBITDAToRevenueMargin'] = sector_df_filtered['EBITDAToEV(%)'] * sector_df_filtered.enterpriseValueToRevenue
        sector_df_filtered.loc[:, 'TotalAssets'] = (sector_df_filtered.marketcap / sector_df_filtered.priceToBook) * (1 + sector_df_filtered.debtToEquity) + sector_df_filtered.currentDebt
        # Alternate Debt + Equity: (sector_df_filtered.enterpriseValue - sector_df_filtered.marketcap + sector_df_filtered.totalCash) * (1 + 1/sector_df_filtered.debtToEquity)
        sector_df_filtered.loc[:, 'EBITDAToAssets(%)'] = sector_df_filtered.EBITDA / sector_df_filtered.TotalAssets

        for col in list(sector_df_filtered.columns):
            if 'Margin' in col or 'Percent' in col or '%' in col:  # scale up ratio by 100 if 'Margin' or 'Percent' in col name
                sector_df_filtered.loc[:, col] *= 100
        x_limits = [-5, min([sector_df_filtered[xaxis].max(), 40])+5] if xaxis == 'EBITDAToEV(%)' else None
        y_limits = [-5, min([sector_df_filtered[yaxis].max(), 80])+5] if yaxis in ['EBITDAToRevenueMargin', 'EBITDAToAssets(%)'] else None
        fig = px.scatter(sector_df_filtered, x=xaxis, y=yaxis, range_x=x_limits, range_y=y_limits,
                        size=sector_df_filtered['enterpriseValue']/1e9, size_max=50, 
                        labels={'size': 'Enterprise Value (billions)', 'index': 'ticker', 'hover_data_1': 'Market Cap (billions)'},
                        color='sector', hover_name='companyName', 
                        hover_data=[sector_df_filtered.index, sector_df_filtered.marketcap/1e9])
        fig.update_layout(
            title=f"Sector Matrix of Valuation for a total of {total_companies} companies, with total Market Cap of {sector_df_filtered.marketcap.sum()/1e12:.3f} trillion, size by Enterprise Value (in billions)",
            legend_title="Sector"
        )
        return [fig]

@app.callback(Output('handler-lastpricestream', 'data'),
[Input('fin-store', 'data'),
Input('price-update-interval', 'n_intervals')])     # for polling of SSE TOPS stream: dcc.Store(id='topsstream-data')
def update_price_stream(df_dict, update_interval):
    # try:
    #     loop = asyncio.get_event_loop()
    # except RuntimeError:
    #     loop = asyncio.new_event_loop()
    try:
        ticker = list(df_dict.keys())[0]
        try:
            stream_data_generator = SSEClient(f"{os.environ.get('IEX_CLOUD_APISSEURL')}tops?token={os.environ.get('IEX_TOKEN')}&symbols={ticker}", timeout=1)
            lastprice_key = 'lastSalePrice'
            lastprice_time_key = 'lastSaleTime'
        except requests.exceptions.ReadTimeout as e:
            logger.exception(str(e) + ' TOPS Quote had Error 503: SSE stream has no data, probably because Market is not open now. Please come back later!')
            stream_data_generator = SSEClient(f"{os.environ.get('IEX_CLOUD_APISSEURL')}last?token={os.environ.get('IEX_TOKEN')}&symbols={ticker}", timeout=1)
            lastprice_key = 'price'
            lastprice_time_key = 'time'
        push_msg = json.loads(next(stream_data_generator).data)
        lastprice = push_msg[0][lastprice_key]
        lastprice_time = time.strftime('%b %d, %Y %H:%M:%S %Z', time.localtime(push_msg[0][lastprice_time_key]/1000))
        return [{'status-info': [html.Br(), f"Last Price {lastprice} @ {lastprice_time}"],
                'supp-data': []}]
    except Exception as e:
        logger.exception(e)
        return [{'status-info': [html.Br(), str(e)], 'supp-data': []}]