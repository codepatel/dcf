import pandas as pd
from datetime import date
from get_fin_report import get_number_from_string, get_string_from_number

# Assumptions for DCF:
TERMINAL_YEAR_LENGTH = 10
TERMINAL_GROWTH_EQ_RISKFREE_RATE = True
CONVERGENCE_PERIOD = 3
MARGINAL_TAX_RATE = 0.29
PROBABILITY_OF_FAILURE = 0.05
MINORITY_INTERESTS = 0
NONOPERATING_ASSETS = 0
OPTIONS_VALUE = 0

def get_dcf_df(df_dict={}, handler_data=[], rgr_next='5', opm_next='10', 
                cagr_2_5='10', opm_target='20', sales_to_cap='1.2', 
                    tax_rate='15', riskfree_rate='3', cost_of_cap='8.5'):
    last_price = float(handler_data[0]['status-info'].split(' @')[0].replace(',', ''))
    df = pd.DataFrame.from_dict(df_dict)
    rgr_next = float(rgr_next)/100
    opm_next = float(opm_next)/100
    cagr_2_5 = float(cagr_2_5)/100
    opm_target = float(opm_target)/100
    tax_rate = float(tax_rate)/100
    riskfree_rate = float(riskfree_rate)/100
    cost_of_cap = float(cost_of_cap)/100
    sales_to_cap = float(sales_to_cap)

    if TERMINAL_GROWTH_EQ_RISKFREE_RATE:
        terminal_growth_rate = riskfree_rate
        delta_rate_late_stage = (cagr_2_5 - terminal_growth_rate) / (TERMINAL_YEAR_LENGTH-5)

    year0_revenue = get_number_from_string(df['Revenue($)'].iloc[-1])
    year0_randd = get_number_from_string(df['Research & Development($)'].iloc[-1])
    year0_ebit = get_number_from_string(df['Pretax Income($)'].iloc[-1]) + year0_randd
    year0_margin = year0_ebit/year0_revenue
    year0_rgr = (get_number_from_string(df['Revenue($)'].iloc[-2])/get_number_from_string(df['Revenue($)'].iloc[0])) ** (1/(len(df)-2)) - 1
    year0_capex = -get_number_from_string(df['Capital Expenditures($)'].iloc[-1])
    year0_ebitlesstax = get_number_from_string(df['Pretax Income($)'].iloc[-1]) * (1-tax_rate) + year0_randd
    year0_reinvestment = year0_capex + year0_randd
    year0_fcf = year0_ebitlesstax - year0_reinvestment

    dcftable = {
        'Revenue($)': [year0_revenue],
        'Revenue Growth(%)': [year0_rgr, rgr_next] + [cagr_2_5] * 4 + 
                    [cagr_2_5-(delta_rate_late_stage * p) for p in range (1, TERMINAL_YEAR_LENGTH-5+1)] + [terminal_growth_rate],
        'EBIT+R&D($)': [year0_ebit],
        'Operating Margin(%)': [year0_margin, opm_next] + 
                    [opm_target if p>CONVERGENCE_PERIOD else opm_target-((opm_target-year0_margin)/CONVERGENCE_PERIOD)*(CONVERGENCE_PERIOD-p) for p in range (2, TERMINAL_YEAR_LENGTH+2)],
        'Tax Rate(%)': [tax_rate] * 6 + [tax_rate + (MARGINAL_TAX_RATE - tax_rate) * p/5 for p in range(1, TERMINAL_YEAR_LENGTH-5+1)] + [MARGINAL_TAX_RATE],
        'EBIT(1-T)($)': [year0_ebitlesstax],
        'Reinvestment($)': [year0_reinvestment],
        'FCF($)': [year0_fcf],
        'CDF(%)': [1],
        'PV_FCF($)': [year0_fcf * 1]
    }
    for period in range(1, TERMINAL_YEAR_LENGTH+2):
        dcftable['Revenue($)'].append(dcftable['Revenue($)'][period-1] * (1+dcftable['Revenue Growth(%)'][period]))
        dcftable['EBIT+R&D($)'].append(dcftable['Revenue($)'][period] * dcftable['Operating Margin(%)'][period])
        dcftable['EBIT(1-T)($)'].append(dcftable['EBIT+R&D($)'][period] * (1 - dcftable['Tax Rate(%)'][period]))
        dcftable['Reinvestment($)'].append((dcftable['Revenue($)'][period]-dcftable['Revenue($)'][period-1])/sales_to_cap if dcftable['Revenue($)'][period] > dcftable['Revenue($)'][period-1] else 0)
        dcftable['FCF($)'].append(dcftable['EBIT(1-T)($)'][period] - dcftable['Reinvestment($)'][period])
        dcftable['CDF(%)'].append(dcftable['CDF(%)'][period-1] / (1+cost_of_cap))
        dcftable['PV_FCF($)'].append(dcftable['FCF($)'][period] * dcftable['CDF(%)'][period])
    
    dcf_output_dict = {}
    dcf_output_dict['terminal_FCF'] = dcftable['FCF($)'][TERMINAL_YEAR_LENGTH+1]
    dcf_output_dict['terminal_value'] = dcf_output_dict['terminal_FCF'] / (cost_of_cap - terminal_growth_rate)
    dcf_output_dict['PV_terminal_value'] = dcf_output_dict['terminal_value'] * dcftable['CDF(%)'][TERMINAL_YEAR_LENGTH]
    dcf_output_dict['PV_sum'] = sum(dcftable['PV_FCF($)'][1:TERMINAL_YEAR_LENGTH+1]) + dcf_output_dict['PV_terminal_value']
    dcf_output_dict['value_operating_assets'] = (1-PROBABILITY_OF_FAILURE) * dcf_output_dict['PV_sum'] + PROBABILITY_OF_FAILURE * (dcf_output_dict['PV_sum']/2)
    dcf_output_dict['book_value_LTdebt'] = get_number_from_string(df['Longterm Debt($)'].iloc[-1])
    dcf_output_dict['cash'] = get_number_from_string(df['Cash($)'].iloc[-1])

    dcf_output_dict['equity_value'] = dcf_output_dict['value_operating_assets'] - dcf_output_dict['book_value_LTdebt'] - MINORITY_INTERESTS + dcf_output_dict['cash'] + NONOPERATING_ASSETS
    dcf_output_dict['common_equity_value'] = dcf_output_dict['equity_value'] - OPTIONS_VALUE
    dcf_output_dict['outstanding_shares'] = get_number_from_string(df['Shares Outstanding'].iloc[-1])
    dcf_output_dict['estimated_value_per_share'] = dcf_output_dict['common_equity_value']/dcf_output_dict['outstanding_shares']
    dcf_output_dict['last_price'] = last_price

    df = pd.DataFrame(dcftable).applymap(get_string_from_number)
    df['Year'] = range(date.today().year, date.today().year+TERMINAL_YEAR_LENGTH+2)
    # df.set_index('Year', inplace=True)
    column_list = list(df.columns)  # column 'Year' move to be first
    df = df.reindex(columns=[column_list[-1]] + column_list[:-1], copy=False)
    
    return df, dcf_output_dict

# %%
if __name__ == "__main__":
    from get_fin_report import get_financial_report
    df_past, a, b, c = get_financial_report('AAPL')
    dcf_df, dcf_dict = get_dcf_df(df_past.to_dict('records'), [{'status-info': '100 @'}])
