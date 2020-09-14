import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import date
from time import sleep
# from functools import lru_cache # https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945
# Local imports
from __init__ import logger, TIMEOUT_12HR
from app import cache

# @lru_cache(maxsize = 100)     # now using Flask-Caching in app.py for sharing memory across instances, sessions, time-based expiry
@cache.memoize(timeout=TIMEOUT_12HR)
def get_financial_report(ticker):
# try:
    urlincome = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials'
    urlbalancesheet = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials/balance-sheet'
    urlcashflow = 'https://www.marketwatch.com/investing/stock/'+ticker+'/financials/cash-flow'
    urlqincome = urlincome + '/income/quarter'
    urlqbalancesheet = urlbalancesheet + '/quarter'
    urlqcashflow = urlcashflow + '/quarter'
    urls = [urlincome, urlbalancesheet, urlcashflow, urlqincome, urlqbalancesheet, urlqcashflow]
    findata_keys = ['ais', 'abs', 'acf', 'qis', 'qbs', 'qcf']

    finsoup = {findata_keys[idx]:get_souped_text(u) for idx, u in enumerate(urls)}

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
    eps = get_element(isdata_lines['eps'],0) + get_element(isdata_lines['eps'],2)
    epsGrowth = get_element(isdata_lines['eps'],1) + get_element(isdata_lines['eps'],3)
    preTaxIncome = get_element(isdata_lines['pretaxincome'],0) + get_element(isdata_lines['pretaxincome'],2)
    netIncome = get_element(isdata_lines['netincome'],1) + get_element(isdata_lines['netincome'],6)
    interestExpense = get_element(isdata_lines['interestexpense'],0) + get_element(isdata_lines['interestexpense'],3)
    resanddev = get_element(isdata_lines['randd'],0) + get_element(isdata_lines['randd'],1)
    ebitda = get_element(isdata_lines['ebitda'],0) + get_element(isdata_lines['ebitda'],3)
    outstanding_shares = get_element(isdata_lines['shares'],0) + get_element(isdata_lines['shares'],1)

    shareholderEquity = get_element(bsdata_lines['equity'],0) + get_element(bsdata_lines['equity'],2)
    longtermDebt = get_element(bsdata_lines['ltd'],0) + get_element(bsdata_lines['ltd'],2)
    totalAssets = get_element(bsdata_lines['totalassets'],1) + get_element(bsdata_lines['totalassets'],6)
    intangibleAssets = get_element(bsdata_lines['intangibleassets'],0) + get_element(bsdata_lines['intangibleassets'],1)
    currentLiabilities = get_element(bsdata_lines['currentliab'],0) + get_element(bsdata_lines['currentliab'],1)
    cash = get_element(bsdata_lines['cash'],0) + get_element(bsdata_lines['cash'],2)

    capEx = get_element(cfdata_lines['capex'],1) + get_element(cfdata_lines['capex'],6)
    fcf = get_element(cfdata_lines['fcf'],0) + get_element(cfdata_lines['fcf'],3)
    
    # load all the data into dataframe 
    df= pd.DataFrame({'Revenue($)': revenue, 'EPS($)': eps, 'EPS Growth(%)': epsGrowth, 
            'Pretax Income($)': preTaxIncome, 'Net Income($)': netIncome, 'Interest Expense($)': interestExpense,
            'EBITDA($)': ebitda, 'Research & Development($)': resanddev, 'Shares Outstanding': outstanding_shares, 
            'Longterm Debt($)': longtermDebt, 'Shareholder Equity($)': shareholderEquity,
            'Total Assets($)': totalAssets, 'Intangible Assets($)': intangibleAssets, 
            'Total Current Liabilities($)': currentLiabilities, 'Cash($)': cash,
            'Capital Expenditures($)': capEx, 'Free Cash Flow($)': fcf
            },index=range(date.today().year-5,date.today().year+1))
    df.reset_index(inplace=True)
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

def get_souped_text(url):
    sleep(0.1)  # throttle scraping
    return BeautifulSoup(requests.get(url).text, features="html.parser") #read in

def get_titles(souptext):
    return souptext.findAll('td', {'class': 'rowTitle'})

def walk_row(titlerow):
    return [td.text for td in titlerow.findNextSiblings(attrs={'class': 'valueCell'}) if td.text]

def get_income_data(data_titles, data_lines):
    def build_income_list(data_list):
        if 'Revenue' in title.text or 'Sales' in title.text or 'Net Interest Income' in title.text:
            data_lines['revenue'].append(data_list)
        if 'EPS (Basic)' in title.text:
            data_lines['eps'].append(data_list)
        if 'Pretax Income' in title.text:
            data_lines['pretaxincome'].append(data_list)
        if 'Net Income' in title.text:
            data_lines['netincome'].append(data_list)
        if 'Total Interest Expense' in title.text:
            data_lines['interestexpense'].append(data_list)
        if 'Research & Development' in title.text:
            data_lines['randd'].append(data_list)
        if 'EBITDA' in title.text:
            data_lines['ebitda'].append(data_list)
        if 'Basic Shares Outstanding' in title.text:
            data_lines['shares'].append(data_list)
    
    for title in data_titles['ais']:
        build_income_list(walk_row(title))

    for title in data_titles['qis']:    # first convert to numbers, then sum
        qtr_data = [get_number_from_string(cell) for cell in walk_row(title)]
        if 'EPS (Basic)' in title.text: # don't scale to 'M' or '%' for pershare
            qtr_sum = f'{sum(qtr_data[1:]):.2f}' if all(v is not None for v in qtr_data) else '-' # use last 4 qtrs for TTM data
        elif 'Basic Shares Outstanding' in title.text:  # don't add the Shares Outstanding, return the last Quarter reported value
            qtr_sum = get_string_from_number(qtr_data[-1])
        else:
            qtr_sum = get_string_from_number(sum(qtr_data[1:])) if all(v is not None for v in qtr_data) else '-' # use last 4 qtrs for TTM data
        build_income_list([qtr_sum])

    return data_lines

def get_balancesheet_data(data_titles, data_lines):
    def build_balancesheet_list(data_list):
        if 'Total Shareholders\' Equity' in title.text:
            data_lines['equity'].append(data_list)
        if 'Long-Term Debt' in title.text:
            data_lines['ltd'].append(data_list)
        if 'Total Assets' in title.text:
            data_lines['totalassets'].append(data_list)
        if 'Intangible Assets' in title.text:
            data_lines['intangibleassets'].append(data_list)
        if 'Total Current Liabilities' in title.text:
            data_lines['currentliab'].append(data_list)
        if 'Cash & Short Term Investments' in title.text:
            data_lines['cash'].append(data_list)
    
    for title in data_titles['abs']:
        build_balancesheet_list(walk_row(title))
    for title in data_titles['qbs']:
        build_balancesheet_list([walk_row(title)[-1]])    # only get MRQ
    
    return data_lines
    
def get_cashflow_data(data_titles, data_lines):
    def build_cashflow_list(data_list):
        if 'Capital Expenditures' in title.text:
            data_lines['capex'].append(data_list)
        if 'Free Cash Flow' in title.text:
            data_lines['fcf'].append(data_list)

    for title in data_titles['acf']:
        build_cashflow_list(walk_row(title))

    for title in data_titles['qcf']:    # first convert to numbers, then sum
        qtr_data = [get_number_from_string(cell) for cell in walk_row(title)]
        qtr_sum = get_string_from_number(sum(qtr_data[1:])) if all(v is not None for v in qtr_data) else '-' # use last 4 qtrs for TTM data
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

@cache.memoize(timeout=TIMEOUT_12HR)
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
    # df, lastprice, lastprice_time, report_date_note = get_financial_report('AAPL')
    pass