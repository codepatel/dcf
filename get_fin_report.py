import os
from datetime import date
from time import sleep
import pandas as pd
from bs4 import BeautifulSoup
import requests
import asyncio
import json
from aiohttp import ClientSession, ClientResponseError
# from aiohttp_sse_client import client as sse_client
from iexfinance.base import _IEXBase
from dotenv import load_dotenv
load_dotenv()
# from functools import lru_cache # https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945
# Local imports
from __init__ import TIMEOUT_12HR, ticker_dict
from app import cache, cache_redis, logger

# @lru_cache(maxsize = 100)     # now using Flask-Caching in app.py for sharing memory across instances, sessions, time-based expiry
@cache.memoize(timeout=TIMEOUT_12HR)
def get_financial_report(ticker):
    if ticker not in ticker_dict():  # Validate with https://sandbox.iexapis.com/stable/ref-data/symbols?token=
        raise ValueError("Invalid Ticker entered: " + ticker)
    urlincome = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials'
    urlbalancesheet = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials/balance-sheet'
    urlcashflow = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials/cash-flow'
    urlqincome = urlincome + '/income/quarter'
    urlqbalancesheet = urlbalancesheet + '/quarter'
    urlqcashflow = urlcashflow + '/quarter'
    urls = [urlincome, urlbalancesheet, urlcashflow, urlqincome, urlqbalancesheet, urlqcashflow]
    findata_keys = ['ais', 'abs', 'acf', 'qis', 'qbs', 'qcf']

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    # future = asyncio.ensure_future(fetch_async(urls, format = 'text'))
    souped_text_list = loop.run_until_complete(fetch_async(urls, format = 'text'))
    finsoup = {k:souped_text_list[idx] for idx, k in enumerate(findata_keys)}

    # build lists for the Financial statements
    isdata_lines = {'revenue': [], 'eps': [], 'pretaxincome': [], 'netincome': [],
                    'interestexpense': [], 'randd': [], 'ebitda': [], 'shares': []
                    }
    bsdata_lines = {'equity': [], 'ltd': [], 'totalassets': [], 'intangibleassets': [], 
                    'currentliab': [], 'cash': []
                    }
    cfdata_lines = {'capex': [], 'fcf': []}

    # find the table headers for the Financial statements
    fin_titles = {k:get_titles(finsoup[k]) for k in findata_keys}

    isdata_lines = get_income_data(fin_titles, isdata_lines)
    bsdata_lines = get_balancesheet_data(fin_titles, bsdata_lines)
    cfdata_lines = get_cashflow_data(fin_titles, cfdata_lines)

    #get the data from the fin statement lists and use helper function get_element to index for format line#
    revenue = get_element(isdata_lines['revenue'],0) + get_element(isdata_lines['revenue'],2)
    revenueGrowth = get_element(isdata_lines['revenue'],1) + get_element(isdata_lines['revenue'],3)
    if len(isdata_lines['revenue']) == 10:    # for Financial companies top-line, add Interest and non-Interest Income
        net_interest_income_after_provision = get_element(isdata_lines['revenue'],2) + get_element(isdata_lines['revenue'],7)
        non_interest_income = get_element(isdata_lines['revenue'],4) + get_element(isdata_lines['revenue'],9)
        revenue = [get_string_from_number(get_number_from_string(net_interest_income_after_provision[y])+get_number_from_string(nii)) for y, nii in enumerate(non_interest_income)]
        revenueGrowth = get_element(isdata_lines['revenue'],3) + get_element(isdata_lines['revenue'],8)
    eps = get_element(isdata_lines['eps'],0) + get_element(isdata_lines['eps'],2)
    epsGrowth = get_element(isdata_lines['eps'],1) + get_element(isdata_lines['eps'],3)
    preTaxIncome = get_element(isdata_lines['pretaxincome'],0) + get_element(isdata_lines['pretaxincome'],2)
    netIncome = get_element(isdata_lines['netincome'],1) + get_element(isdata_lines['netincome'],6)
    interestExpense = get_element(isdata_lines['interestexpense'],0) + (get_element(isdata_lines['interestexpense'],3) if len(isdata_lines['interestexpense'][3]) ==1 else get_element(isdata_lines['interestexpense'],4))
    resanddev = get_element(isdata_lines['randd'],0) + get_element(isdata_lines['randd'],1)
    ebitda = get_element(isdata_lines['ebitda'],0) + get_element(isdata_lines['ebitda'],3)
    outstanding_shares = get_element(isdata_lines['shares'],0) + get_element(isdata_lines['shares'],1)

    shareholderEquity = get_element(bsdata_lines['equity'],0) + get_element(bsdata_lines['equity'],2)
    longtermDebt = get_element(bsdata_lines['ltd'],0) + get_element(bsdata_lines['ltd'],1)
    if bsdata_lines['totalassets'][1][0] != '-':
        totalAssets = get_element(bsdata_lines['totalassets'],1) + get_element(bsdata_lines['totalassets'],6)
    else:
        totalAssets = get_element(bsdata_lines['totalassets'],0) + get_element(bsdata_lines['totalassets'],5)
    if get_number_from_string(totalAssets[0]) < 10:
        totalAssets = get_element(bsdata_lines['totalassets'],0) + get_element(bsdata_lines['totalassets'],4)
    intangibleAssets = get_element(bsdata_lines['intangibleassets'],0) + get_element(bsdata_lines['intangibleassets'],1)
    currentLiabilities = get_element(bsdata_lines['currentliab'],0) + get_element(bsdata_lines['currentliab'],1)
    if all([c == '-' for c in currentLiabilities]):
        currentLiabilities = ['0'] * len(totalAssets)
    cash = get_element(bsdata_lines['cash'],0) + get_element(bsdata_lines['cash'],2)
    
    capEx = get_element(cfdata_lines['capex'],0) + get_element(cfdata_lines['capex'],1)
    fcf = get_element(cfdata_lines['fcf'],0) + get_element(cfdata_lines['fcf'],1)
    
    # load all the data into dataframe 
    df= pd.DataFrame({'Revenue($)': revenue, 'Revenue Growth(%)': revenueGrowth, 'EPS($)': eps, 'EPS Growth(%)': epsGrowth, 
            'Pretax Income($)': preTaxIncome, 'Net Income($)': netIncome, 'Interest Expense($)': interestExpense,
            'EBITDA($)': ebitda, 'Research & Development($)': resanddev, 'Shares Outstanding': outstanding_shares, 
            'Longterm Debt($)': longtermDebt, 'Shareholder Equity($)': shareholderEquity,
            'Total Assets($)': totalAssets, 'Intangible Assets($)': intangibleAssets, 
            'Total Current Liabilities($)': currentLiabilities, 'Cash($)': cash,
            'Net Investing Cash Flow($)': capEx, 'Free Cash Flow($)': fcf
            },index=range(date.today().year-5,date.today().year+1))
    df.reset_index(inplace=True)
    # Derived Financial Metrics/Ratios
    df['Net Profit Margin(%)'] = (df['Net Income($)'].apply(get_number_from_string) / df['Revenue($)'].apply(get_number_from_string)).apply(get_string_from_number)
    df['Capital Employed($)'] = df['Total Assets($)'].apply(get_number_from_string) - df['Total Current Liabilities($)'].apply(get_number_from_string)
    df['Sales-to-Capital(%)'] = (df['Revenue($)'].apply(get_number_from_string) / df['Capital Employed($)']).apply(get_string_from_number)
    df['ROCE(%)'] = (df['Net Income($)'].apply(get_number_from_string) / df['Capital Employed($)']).apply(get_string_from_number)
    df['Capital Employed($)'] = df['Capital Employed($)'].apply(get_string_from_number)

    try:
        lastprice = finsoup['ais'].findAll('p', {'class': 'data bgLast'})[0].text
        lastprice_time = finsoup['ais'].findAll('p', {'class': 'lastcolumn bgTimestamp longformat'})[0].text
        fiscal_year_note = finsoup['ais'].findAll('th', {'class': 'rowTitle'})[0].text.split('.')[0]
        mrq_date = finsoup['qis'].findAll('th', {'scope': 'col'})[-2].text
        report_date_note = mrq_date + ", " + fiscal_year_note
    except IndexError:
        raise IndexError("Data not found for Ticker: " + ticker)

    return df, lastprice, lastprice_time, report_date_note

@cache_redis.memoize(timeout=TIMEOUT_12HR*2*7)    # weekly update
def get_sector_data(sector):
    """
    Get sector data from iexfinance API
    """
    try:
        # ONLY US-listed stocks in NYSE, NASDAQ
        stocks = [s for s in SectorCollection(sector).fetch() if 'primaryExchange' in s and ''.join(sorted(s['primaryExchange'])).strip() in ['ENSYacceeghkknoortwx', 'AADNQS']]
        logger.info(f'\t{sector}\tUS-listed:\t{len(stocks)}\tcompanies.')
        # If we can't see its PE here, we're probably not interested in a stock. Omit it from batch queries.
        stocks = [s for s in stocks if s['peRatio'] and s['peRatio']>0]
        logger.info(f'\t{sector}\tPE>0:\t{len(stocks)}\tcompanies.')
        # IEX doesn't like batch queries for more than 100 symbols at a time.
        # We need to build our fundamentals info iteratively.
        batch_idx = 0
        batch_size = 100
        adv_stats_api_urls = []
        resp_dict = {}
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        while batch_idx < len(stocks):
            symbol_batch = [s['symbol']
                            for s in stocks[batch_idx:batch_idx+batch_size]]
            adv_stats_api_urls.append(os.environ.get('IEX_CLOUD_APIURL') 
                                + 'stock/market/batch?symbols=' + ','.join(symbol_batch) + '&types=advanced-stats&token=' 
                                + os.environ.get('IEX_TOKEN'))
            batch_idx += batch_size
        # limit to 300 companies per sector for getting advanced-stats endpoint, 
        # TODO: improve this in future
        for d in loop.run_until_complete(fetch_async(adv_stats_api_urls[:3], format = 'json')):
            resp_dict.update(d)
        logger.info(f'\t{sector}\tGot data for:\t{len(resp_dict)}\tcompanies.')
        return resp_dict
    except Exception as e:
        logger.exception(e)

# We extend iexfinance a bit to support the sector collection endpoint.
class SectorCollection(_IEXBase):

    def __init__(self, sector, **kwargs):
        self.sector = sector
        self.output_format = 'json'
        super(SectorCollection, self).__init__(**kwargs)

    @property
    def url(self):
        return '/stock/market/collection/sector?collectionName={}'.format(self.sector)

async def fetch_async(urls, format = 'text'):
    tasks = []
    # try to use one client session
    async with ClientSession() as session:
        for url in urls:
            if format == 'text':
                task = asyncio.ensure_future(get_souped_text(session, url))
            elif format == 'json':
                task = asyncio.ensure_future(get_json_resp(session, url))
            else:
                raise ValueError('Invalid format for fetching URL: ' + format)
            tasks.append(task)
        # await response outside the for loop
        resp_list = await asyncio.gather(*tasks)
    return resp_list

async def get_souped_text(session, url):
    # sleep(0.1)  # throttle scraping
    try:
        async with session.get(url, timeout=15) as response:
            resp = await response.read()
        return BeautifulSoup(resp.decode('utf-8'), features="html.parser")  # read in
    except ClientResponseError as e:
        logger.error(e.code)
    except asyncio.TimeoutError:
        logger.error("Timeout")
    except Exception as e:
        logger.exception(e)

async def get_json_resp(session, url):
    async with session.get(url) as resp:
        resp = await resp.json()
    return resp

# async def get_stream_quote(ticker):
#     async with sse_client.EventSource(
#         f"{os.environ.get('IEX_CLOUD_APISSEURL')}tops?token={os.environ.get('IEX_TOKEN')}&symbols={ticker}"
#         ) as event_source:
#         try:
#             async for event in event_source:
#                 logger.info(event)
#                 return event
#         except ConnectionError as e:
#             logger.exception(e)

def get_titles(souptext):
    return souptext.findAll('td', {'class': 'rowTitle'})

def walk_row(titlerow):
    return [td.text for td in titlerow.findNextSiblings(attrs={'class': 'valueCell'}) if td.text]

def get_income_data(data_titles, data_lines):
    def build_income_list(data_list):
        if 'Sales' in title.text \
                or 'Net Interest Inc' in title.text or 'Non-Interest Income' in title.text:     # for Financial companies top-line
            data_lines['revenue'].append(data_list)
        if 'EPS (Diluted)' in title.text:
            data_lines['eps'].append(data_list)
        if 'Pretax Income' in title.text:
            data_lines['pretaxincome'].append(data_list)
        if 'Net Income' in title.text:
            data_lines['netincome'].append(data_list)
        if ' Interest Expense' in title.text:
            data_lines['interestexpense'].append(data_list)
        if 'Research & Development' in title.text:
            data_lines['randd'].append(data_list)
        if 'EBITDA' in title.text:
            data_lines['ebitda'].append(data_list)
        if 'Diluted Shares Outstanding' in title.text:
            data_lines['shares'].append(data_list)
    
    for title in data_titles['ais']:
        build_income_list(walk_row(title))

    for title in data_titles['qis']:    # first convert to numbers, then sum
        qtr_data = [get_number_from_string(cell) for cell in walk_row(title)]
        if 'EPS (Diluted)' in title.text: # don't scale to 'M' or '%' for pershare
            qtr_sum = f'{sum(qtr_data[1:]):.2f}' if all(v is not None for v in qtr_data[1:]) else '-' # use last 4 qtrs for TTM data
        elif 'Diluted Shares Outstanding' in title.text:  # don't add the Shares Outstanding, return the last Quarter reported value
            qtr_sum = get_string_from_number(qtr_data[-1])
        else:
            qtr_sum = get_string_from_number(sum(qtr_data[1:])) if all(v is not None for v in qtr_data[1:]) else '-' # use last 4 qtrs for TTM data
        build_income_list([qtr_sum])

    return data_lines

def get_balancesheet_data(data_titles, data_lines):
    def build_balancesheet_list(data_list):
        if 'Total Shareholders\' Equity' in title.text:
            data_lines['equity'].append(data_list)
        if 'Debt excl. Capital' in title.text:
            data_lines['ltd'].append(data_list)
        if 'Total Assets' in title.text:
            data_lines['totalassets'].append(data_list)
        if 'Intangible Assets' in title.text:
            data_lines['intangibleassets'].append(data_list)
        if 'Total Current Liabilities' in title.text:
            data_lines['currentliab'].append(data_list)
        if 'Cash & Short Term Investments' in title.text or 'Cash & Due from' in title.text:
            data_lines['cash'].append(data_list)
    
    for title in data_titles['abs']:
        build_balancesheet_list(walk_row(title))
    for title in data_titles['qbs']:
        build_balancesheet_list([walk_row(title)[-1]])    # only get MRQ
    
    return data_lines
    
def get_cashflow_data(data_titles, data_lines):
    def build_cashflow_list(data_list):
        if ' Net Investing Cash Flow' in title.text:
            data_lines['capex'].append(data_list)
        if ' Free Cash Flow' in title.text:
            data_lines['fcf'].append(data_list)

    for title in data_titles['acf']:
        build_cashflow_list(walk_row(title))

    for title in data_titles['qcf']:    # first convert to numbers, then sum
        qtr_data = [get_number_from_string(cell) for cell in walk_row(title)]
        qtr_sum = get_string_from_number(sum(qtr_data[1:])) if all(v is not None for v in qtr_data[1:]) else '-' # use last 4 qtrs for TTM data
        build_cashflow_list([qtr_sum])
    
    return data_lines

def get_element(list, element):
    try:
        return list[element]
    except:
        return '-'

def get_number_from_string(str_value):
    try:
        if isinstance(str_value, str):
            str_value = str_value.replace(',', '')  # remove commas for formatting
            if str_value[0] == '(': # negative number in parenthesis format
                str_value = '-' + str_value[1:-1]
            if str_value == '-' or str_value == '--':
                return None
            else:
                try:
                    return float(str_value)
                except ValueError:
                    units_dict = {'M': 1e6, 'B': 1e9, 'T': 1e12, '%': 0.01}
                    return float(str_value[:-1]) * units_dict[str_value[-1]]
        else:
            raise ValueError('Need a string input to convert to number!')
    except Exception as e:
        logger.exception(e)
        return None


def get_string_from_number(num_value):
    if abs(num_value) > 1e12:
        return '{:.2f}'.format(num_value/1e12) + 'T' if num_value >= 0 else '(' + '{:.2f}'.format(-num_value/1e12) + 'T)'
    if abs(num_value) > 1e9:
        return '{:.2f}'.format(num_value/1e9) + 'B' if num_value >= 0 else '(' + '{:.2f}'.format(-num_value/1e9) + 'B)'
    if abs(num_value) > 1e6:
        return '{:.2f}'.format(num_value/1e6) + 'M' if num_value >= 0 else '(' + '{:.2f}'.format(-num_value/1e6) + 'M)'
    if abs(num_value) < 10: # < 10 i.e. assume ratio < 1000% 
        return '{:.2f}'.format(num_value*100) + '%' if num_value >= 0 else '(' + '{:.2f}'.format(-num_value*100) + '%)'
    return '{:.2f}'.format(num_value)

@cache.memoize(timeout=TIMEOUT_12HR*2*7)    # weekly update
def get_yahoo_fin_values(ticker):
    urlmain = 'https://finance.yahoo.com/quote/'+ticker+'/'
    try:
        s = BeautifulSoup(requests.get(urlmain).text, features="html.parser")
        beta = float(s.findAll('td', {'class': 'Ta(end) Fw(600) Lh(14px)', 'data-reactid': '143'})[0].text)
        next_earnings_date = s.findAll('td', {'class': 'Ta(end) Fw(600) Lh(14px)', 'data-reactid': '158'})[0].text
        return next_earnings_date, beta
    except Exception as e:
        logger.exception(e)
        return 'N/A', []

# %%
if __name__ == '__main__':
    import cProfile
    import pstats
    pr = cProfile.Profile()
    pr.enable()
    df, lastprice, lastprice_time, report_date_note = get_financial_report('AAPL')
    pr.disable()
    pstats.Stats(pr).strip_dirs().sort_stats('time').print_stats(0.05)  # Profile only Top 5% time spent