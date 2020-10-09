import pandas as pd
from datetime import date
from get_fin_report import get_number_from_string, get_string_from_number

# Assumptions for DCF:
TERMINAL_YEAR_LENGTH = 10

def get_dcf_df(df_dict=[], rgr_next='5', opm_next='10', 
                cagr_2_5='10', opm_target='20', sales_to_cap='1.2', 
                    tax_rate='15', riskfree_rate='3', terminal_growth_rate='3',  
                    cost_of_cap='8.5', run_dcf_button_clicks=None, *args):
    """
    Calculate the Discounted Cash Flow Outputs and return a df with the table information
    """
    last_price = list(df_dict.values())[0]['stats_dict']['lastprice']

    rgr_next = float(rgr_next)/100
    opm_next = float(opm_next)/100
    cagr_2_5 = float(cagr_2_5)/100
    opm_target = float(opm_target)/100
    tax_rate = float(tax_rate)/100
    riskfree_rate = float(riskfree_rate)/100
    cost_of_cap = float(cost_of_cap)/100
    sales_to_cap = float(sales_to_cap)

    # From dynamic updates of update_current_year_values
    year0_revenue = args[0]*1e6
    year0_randd = args[1]*1e6
    year0_capex = args[2]*1e6
    year0_ebit = args[3]*1e6
    year0_rgr = args[4]/100
    year0_cash = args[5]*1e6
    year0_ltdebt = args[6]*1e6
    year0_shares = args[7]*1e6
    minority_interests = args[8]*1e6
    nonoperating_assets = args[9]*1e6
    options_value = args[10]*1e6
    # From dynamic updates of user input
    convergence_year = args[11]
    marginal_tax_rate = args[12]/100
    probability_of_failure = args[13]/100
    terminal_growth_eq_riskfree_rate = args[14]

    if terminal_growth_eq_riskfree_rate:
        terminal_growth_rate = riskfree_rate
    else:
        terminal_growth_rate = float(terminal_growth_rate)/100
    
    delta_rate_late_stage = (cagr_2_5 - terminal_growth_rate) / (TERMINAL_YEAR_LENGTH-5)

    year0_margin = year0_ebit/year0_revenue
    year0_ebitlesstax = (year0_ebit - year0_randd) * (1-tax_rate) + year0_randd
    year0_reinvestment = (year0_revenue * year0_rgr / sales_to_cap) + year0_randd
    year0_fcf = year0_ebitlesstax - year0_reinvestment
    year0_randd_to_revenue = year0_randd/year0_revenue

    dcftable = {
        'Revenue($)': [year0_revenue],
        'Revenue Growth(%)': [year0_rgr, rgr_next] + [cagr_2_5] * 4 + 
                    [cagr_2_5-(delta_rate_late_stage * p) for p in range (1, TERMINAL_YEAR_LENGTH-5+1)] + [terminal_growth_rate],
        'EBIT+R&D($)': [year0_ebit],
        'Operating Margin(%)': [year0_margin, opm_next] + 
                    [opm_target if p>convergence_year else opm_target-((opm_target-year0_margin)/convergence_year)*(convergence_year-p) for p in range (2, TERMINAL_YEAR_LENGTH+2)],
        'Tax Rate(%)': [tax_rate] * 6 + [tax_rate + (marginal_tax_rate - tax_rate) * p/5 for p in range(1, TERMINAL_YEAR_LENGTH-5+1)] + [marginal_tax_rate],
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
        capitalized_randd = year0_randd_to_revenue * dcftable['Revenue($)'][period] * (1-0.02*period)
        dcftable['Reinvestment($)'].append((dcftable['Revenue($)'][period]-dcftable['Revenue($)'][period-1])/sales_to_cap + (capitalized_randd) if dcftable['Revenue Growth(%)'][period]>0 else capitalized_randd)
        dcftable['FCF($)'].append(dcftable['EBIT(1-T)($)'][period] - dcftable['Reinvestment($)'][period])
        dcftable['CDF(%)'].append(dcftable['CDF(%)'][period-1] / (1+cost_of_cap))
        dcftable['PV_FCF($)'].append(dcftable['FCF($)'][period] * dcftable['CDF(%)'][period])
    
    dcf_output_dict = {}
    dcf_output_dict['terminal_FCF'] = dcftable['FCF($)'][TERMINAL_YEAR_LENGTH+1]
    dcf_output_dict['terminal_value'] = dcf_output_dict['terminal_FCF'] / (cost_of_cap - terminal_growth_rate)
    dcf_output_dict['PV_terminal_value'] = dcf_output_dict['terminal_value'] * dcftable['CDF(%)'][TERMINAL_YEAR_LENGTH]
    dcf_output_dict['PV_sum'] = sum(dcftable['PV_FCF($)'][1:TERMINAL_YEAR_LENGTH+1]) + dcf_output_dict['PV_terminal_value']
    dcf_output_dict['value_operating_assets'] = (1-probability_of_failure) * dcf_output_dict['PV_sum'] + probability_of_failure * (dcf_output_dict['PV_sum']/2)
    dcf_output_dict['book_value_LTdebt'] = year0_ltdebt
    dcf_output_dict['cash'] = year0_cash

    dcf_output_dict['equity_value'] = dcf_output_dict['value_operating_assets'] - dcf_output_dict['book_value_LTdebt'] - minority_interests + dcf_output_dict['cash'] + nonoperating_assets
    dcf_output_dict['common_equity_value'] = dcf_output_dict['equity_value'] - options_value
    dcf_output_dict['outstanding_shares'] = year0_shares
    dcf_output_dict['estimated_value_per_share'] = dcf_output_dict['common_equity_value']/dcf_output_dict['outstanding_shares']
    dcf_output_dict['last_price'] = last_price

    df = pd.DataFrame(dcftable).applymap(get_string_from_number)
    current_year = date.today().year if date.today().month>2 else date.today().year-1
    df['Year'] = range(current_year, current_year+TERMINAL_YEAR_LENGTH+2)
    # df.set_index('Year', inplace=True)
    column_list = list(df.columns)  # column 'Year' move to be first
    df = df.reindex(columns=[column_list[-1]] + column_list[:-1], copy=False)
    
    return df, dcf_output_dict
