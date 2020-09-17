from statistics import mean
from app import app
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
# Local imports
from __init__ import logger
from get_fin_report import get_number_from_string

def get_dcf_current_year_input_overrides():
    return dbc.Form([dbc.FormGroup(
                [
                    dbc.Label("Revenue(M$)", html_for="year0-revenue"),
                    dbc.Input(
                        type="number",
                        id="year0-revenue",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("R&D(M$)", html_for="year0-randd"),
                    dbc.Input(
                        type="number",
                        id="year0-randd",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("CapEx(M$)", html_for="year0-capex"),
                    dbc.Input(
                        type="number",
                        id="year0-capex",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("EBIT excl. Reinvestment(M$)", html_for="year0-ebit"),
                    dbc.Input(
                        type="number",
                        id="year0-ebit",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Past Revenue CAGR(%)", html_for="year0-rgr"),
                    dbc.Input(
                        type="number",
                        id="year0-rgr",
                        disabled=True,
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Minority Interests(M$)", html_for="minority-interests"),
                    dbc.Input(
                        type="number", value=0,
                        id="minority-interests",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Nonoperating Assets(M$)", html_for="nonoperating-assets"),
                    dbc.Input(
                        type="number", value=0,
                        id="nonoperating-assets",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Employee Options Value(M$)", html_for="options-value"),
                    dbc.Input(
                        type="number", value=0,
                        id="options-value",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),], inline=True)

def get_other_input_overrides():
    return dbc.Form([dbc.FormGroup(
                [
                    dbc.Label("Convergence Year", html_for="convergence-year"),
                    dcc.Slider(id="convergence-year", min=2, max=8, step=1, value=3,
                    marks={v: str(v) for v in range(2, 9)},
                    )
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Marginal Tax Rate(%)", html_for="marginal-tax"),
                    dcc.Slider(id="marginal-tax", min=15, max=50, step=1, value=29,
                    marks={v: str(v) for v in range(15, 50, 5)},
                    )
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Probability of Failure(%)", html_for="prob-failure"),
                    dcc.Slider(id="prob-failure", min=0, max=99, step=5, value=0,
                    marks={v: str(v) for v in range(0, 101, 5)},
                    )
                ]
        ),])

@app.callback([Output('year0-revenue', 'value'),
Output('year0-randd', 'value'),
Output('year0-capex', 'value'),
Output('year0-ebit', 'value'),
Output('year0-rgr', 'value'),
Output('cagr-2-5', 'value'),
Output('opm-target', 'value'),
Output('sales-to-cap', 'value')],
[Input('fin-df', 'data')])
def update_current_year_values(df_dict):
    if not df_dict:
        raise PreventUpdate
    try:
        for y in df_dict:
            if y['Research & Development($)'] == '-' or y['Research & Development($)'] == '--':
                y['Research & Development($)'] = '0'
        year0_dict = df_dict[-1]
        year0_revenue = get_number_from_string(year0_dict['Revenue($)'])/1e6
        year0_randd = get_number_from_string(year0_dict['Research & Development($)'])/1e6
        year0_ebit = get_number_from_string(year0_dict['Pretax Income($)'])/1e6 + year0_randd
        year0_capex = -round(get_number_from_string(year0_dict['Capital Expenditures($)']))/1e6
        year0_rgr = round(100 * ((get_number_from_string(df_dict[-2]['Revenue($)'])/get_number_from_string(df_dict[0]['Revenue($)'])) ** (1/(len(df_dict)-2)) - 1), 2)

        cagr_2_5 = min(year0_rgr, 15)    # starting point same as past performance
        opm_target = min(100 * mean([ (get_number_from_string(y['Pretax Income($)']) + get_number_from_string(y['Research & Development($)']) )/
                            get_number_from_string(y['Revenue($)']) for y in df_dict]), 50 )
        sales_to_cap = max(0.05, mean([get_number_from_string(y['Sales-to-Capital(%)']) for y in df_dict]) )

        return year0_revenue, year0_randd, year0_capex, year0_ebit, year0_rgr, cagr_2_5, opm_target, sales_to_cap
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate


@app.callback([Output('cost-of-cap', 'value')],
[Input('fin-df', 'data'),
Input('stats-df', 'data'),
Input('erp-calculated', 'value'),
Input('tax-rate', 'value'),
Input('riskfree-rate', 'value')])
def get_cost_of_capital(df_dict, stats_dict, erp, tax_rate, riskfree_rate):
    if not df_dict or not stats_dict or not erp:
        raise PreventUpdate
    try:
        year0_dict = df_dict[-1]
        equity_market_value = get_number_from_string(year0_dict['Shares Outstanding']) * stats_dict[0]['lastprice']
        beta = stats_dict[0]['beta'] if stats_dict[0]['beta'] else 1
        debt_book_value = get_number_from_string(year0_dict['Longterm Debt($)'])
        interest_expense_debt = get_number_from_string(year0_dict['Interest Expense($)']) if get_number_from_string(year0_dict['Interest Expense($)']) else 0
        average_maturity = 3
        pretax_cost_of_debt = 0.04
        convertible_debt_book_value = 0

        # =B19*(1-(1+B25)^(-B20))/B25+B18/(1+B25)^B20
        debt_market_value = (interest_expense_debt * (1-(1+pretax_cost_of_debt) ** (-average_maturity)) / pretax_cost_of_debt) + (debt_book_value / ((1+pretax_cost_of_debt) ** average_maturity))
        convertible_market_value = 0
        convertible_debt_portion_market_value = 0
        convertible_equity_portion_market_value = convertible_market_value - convertible_debt_portion_market_value
        preferred_num_shares = 0
        preferred_price_pershare = 70
        preferred_dividend_pershare = 5

        debt_value_op_leases = 0
        total_debt = debt_market_value + convertible_debt_portion_market_value + debt_value_op_leases

        cap_structure_list = [equity_market_value, preferred_num_shares * preferred_price_pershare, total_debt]
        total_capital = sum(cap_structure_list)
        wcc = [c/total_capital for c in cap_structure_list]
        coc = [riskfree_rate + (beta * erp), 
                preferred_dividend_pershare/preferred_price_pershare, 
                pretax_cost_of_debt * (1-tax_rate)]

        return [sum([wcc[c]*rate for c, rate in enumerate(coc)])]
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate