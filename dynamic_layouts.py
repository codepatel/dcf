from statistics import mean
import json
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
# Local imports
from app import app, db, logger
from get_fin_report import get_number_from_string

def get_dcf_current_year_input_overrides():
    return [dbc.Form([dbc.FormGroup(
                [
                    dbc.Label("Revenue (M$)", html_for="year0-revenue"),
                    dbc.Input(
                        type="number",
                        id="year0-revenue",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("R&D (M$)", html_for="year0-randd"),
                    dbc.Input(
                        type="number",
                        id="year0-randd",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("CapEx (M$)", html_for="year0-capex"),
                    dbc.Input(
                        type="number",
                        id="year0-capex",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("EBIT excl. Reinvestment (M$)", html_for="year0-ebit"),
                    dbc.Input(
                        type="number",
                        id="year0-ebit",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Past Revenue CAGR (%)", html_for="year0-rgr"),
                    dbc.Input(
                        type="number",
                        id="year0-rgr",
                        disabled=True,
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Cash and Equivalents (M$)", html_for="cash"),
                    dbc.Input(
                        type="number", value=0,
                        id="cash",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Common Shares Outstanding (Millions)", html_for="shares-outstanding"),
                    dbc.Input(
                        type="number", value=0,
                        id="shares-outstanding",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Minority Interests (M$)", html_for="minority-interests"),
                    dbc.Input(
                        type="number", value=0,
                        id="minority-interests",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Nonoperating Assets (M$)", html_for="nonoperating-assets"),
                    dbc.Input(
                        type="number", value=0,
                        id="nonoperating-assets",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Employee Options Value (M$)", html_for="options-value"),
                    dbc.Input(
                        type="number", value=0,
                        id="options-value",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Book Value of Longterm Debt (M$)", html_for="debt-book-value"),
                    dbc.Input(
                        type="number", value=0,
                        id="debt-book-value",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Interest Expense (M$)", html_for="interest-expense"),
                    dbc.Input(
                        type="number", value=0,
                        id="interest-expense",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Convertible Debt Book Value (M$)", html_for="convertible-debt-book-value"),
                    dbc.Input(
                        type="number", value=0,
                        id="convertible-debt-book-value",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Convertible Market Value (M$)", html_for="convertible-market-value"),
                    dbc.Input(
                        type="number", value=0,
                        id="convertible-market-value",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Preferred Equity Number of Shares (Millions)", html_for="preferred-num-shares"),
                    dbc.Input(
                        type="number", value=0,
                        id="preferred-num-shares",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Preferred Price per share ($)", html_for="preferred-price-pershare"),
                    dbc.Input(
                        type="number", value=70,
                        id="preferred-price-pershare",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Preferred Dividend per share ($)", html_for="preferred-dividend-pershare"),
                    dbc.Input(
                        type="number", value=5, min=0.01, step=0.01,
                        id="preferred-dividend-pershare",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Debt Value of Operating Leases (M$)", html_for="debt-value-op-leases"),
                    dbc.Input(
                        type="number", value=0,
                        id="debt-value-op-leases",
                        placeholder="Enter number", debounce=True
                    ),
                ]
        ),
        ], inline=True),
        dbc.Form([dbc.FormGroup(
                [
                    dbc.Label("Average Maturity Duration (years)", html_for="average-maturity"),
                    dcc.Slider(id="average-maturity", min=2, max=10, step=0.25, value=3,
                    marks={v: str(v) for v in range(2, 11)},
                    )
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Pretax Cost of Debt (%)", html_for="pretax-cost-debt"),
                    dcc.Slider(id="pretax-cost-debt", min=2, max=10, step=0.25, value=4,
                    marks={v: str(v) for v in range(2, 11)},
                    )
                ]
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Convertible Debt Portion of Market Value (%)", html_for="convertible-debt-portion"),
                    dcc.Slider(id="convertible-debt-portion", min=0, max=100, step=5, value=0,
                    marks={v: str(v) for v in range(0, 101, 5)},
                    )
                ]
        ),
        ])]

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
        ),
        dbc.FormGroup(
                [
                    dbc.Label("Override default assumptions:"),
                    dbc.Checklist(
                    options=[
                        {"label": "Terminal Growth Rate = Riskfree Rate?", "value": 1},
                    ],
                    value=[],
                    id="override-default-assumptions",
                    switch=True,
                    ),
                ]
        ),
    ])

@app.callback([Output('year0-revenue', 'value'),
Output('year0-randd', 'value'),
Output('year0-capex', 'value'),
Output('year0-ebit', 'value'),
Output('year0-rgr', 'value'),
Output('rgr-next', 'value'),
Output('opm-next', 'value'),
Output('cagr-2-5', 'value'),
Output('opm-target', 'value'),
Output('sales-to-cap', 'value'),
Output('debt-book-value', 'value'),
Output('interest-expense', 'value'),
Output('cash', 'value'),
Output('shares-outstanding', 'value')],
[Input('fin-store', 'data')],
[State('analysis-mode', 'value'),
State('snapshot-uuid', 'value'),])
def update_current_year_values(df_dict, live_analysis_mode, snapshot_uuid):
    if not df_dict:
        raise PreventUpdate
    try:
        ticker = list(df_dict.keys())[0]
        dcf_store_dict_json = db.get(ticker+'-'+snapshot_uuid)
        dcf_store_dict = json.loads(dcf_store_dict_json) if dcf_store_dict_json else None
        safe_get_year0_revenue = dcf_store_dict.get(ticker).get('year0-revenue.value') if dcf_store_dict else None
        if 1 in live_analysis_mode or not safe_get_year0_revenue:
            df_dict = list(df_dict.values())[0]['fin_report_dict']
            for y in df_dict:
                if y['Research & Development($)'] == '-' or y['Research & Development($)'] == '--':
                    y['Research & Development($)'] = '0'
            year0_dict = df_dict[-1]
            year0_revenue = get_number_from_string(year0_dict['Revenue($)'])/1e6
            year0_randd = get_number_from_string(year0_dict['Research & Development($)'])/1e6
            year0_ebit = get_number_from_string(year0_dict['Pretax Income($)'])/1e6 + year0_randd
            year0_capex = -round(get_number_from_string(year0_dict['Net Investing Cash Flow($)']))/1e6
            year0_rgr = round(100 * ((get_number_from_string(df_dict[-2]['Revenue($)'])/get_number_from_string(df_dict[0]['Revenue($)'])) ** (1/(len(df_dict)-2)) - 1), 2)
            # starting point same as past performance            
            cagr_2_5 = min(year0_rgr, 15)
            opm_target = min(100 * mean([ (get_number_from_string(y['Pretax Income($)']) + get_number_from_string(y['Research & Development($)']) )/
                                get_number_from_string(y['Revenue($)']) for y in df_dict]), 50 )
            rgr_next = round(0.5 * cagr_2_5, 1)
            opm_next = round(0.5 * opm_target, 1)
            sales_to_cap = max(0.05, mean([get_number_from_string(y['Sales-to-Capital(%)']) for y in df_dict]) )

            debt_book_value = (get_number_from_string(year0_dict['Longterm Debt($)']) or 0)/1e6
            interest_expense_debt = (get_number_from_string(year0_dict['Interest Expense($)']) or 0)/1e6
            cash = (get_number_from_string(year0_dict['Cash($)']) or 0)/1e6
            shares_outstanding = get_number_from_string(year0_dict['Shares Outstanding'])/1e6
        else:
            year0_revenue = safe_get_year0_revenue or 0
            year0_randd = dcf_store_dict.get(ticker).get('year0-randd.value') or 0
            year0_capex = dcf_store_dict.get(ticker).get('year0-capex.value') or 0
            year0_ebit = dcf_store_dict.get(ticker).get('year0-ebit.value') or 0
            year0_rgr = dcf_store_dict.get(ticker).get('year0-rgr.value') or 0
            rgr_next = dcf_store_dict.get(ticker).get('rgr-next.value') or 0
            opm_next = dcf_store_dict.get(ticker).get('opm-next.value') or 0
            cagr_2_5 = dcf_store_dict.get(ticker).get('cagr-2-5.value') or 0
            opm_target = dcf_store_dict.get(ticker).get('opm-target.value') or 0
            sales_to_cap = dcf_store_dict.get(ticker).get('sales-to-cap.value') or 0
            debt_book_value = dcf_store_dict.get(ticker).get('debt-book-value.value') or 0
            interest_expense_debt = dcf_store_dict.get(ticker).get('interest-expense.value') or 0
            cash = dcf_store_dict.get(ticker).get('cash.value') or 0
            shares_outstanding = dcf_store_dict.get(ticker).get('shares-outstanding.value') or 0

        return year0_revenue, year0_randd, year0_capex, year0_ebit, year0_rgr, rgr_next, opm_next, cagr_2_5, opm_target, sales_to_cap, debt_book_value, interest_expense_debt, cash, shares_outstanding
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate


@app.callback([Output('cost-of-cap', 'value')],
[Input('fin-store', 'data'),
Input('debt-book-value', 'value'),
Input('interest-expense', 'value'),
Input('average-maturity', 'value'),
Input('pretax-cost-debt', 'value'),
Input('convertible-debt-book-value', 'value'),
Input('convertible-market-value', 'value'),
Input('convertible-debt-portion', 'value'),
Input('preferred-num-shares', 'value'),
Input('preferred-price-pershare', 'value'),
Input('preferred-dividend-pershare', 'value'),
Input('debt-value-op-leases', 'value'),
Input('erp-calculated', 'value'),
Input('tax-rate', 'value'),
Input('riskfree-rate', 'value')],
[State('terminal-growth-rate', 'disabled'),
State('terminal-growth-rate', 'value'),
State('analysis-mode', 'value'),
State('snapshot-uuid', 'value'),])
def get_cost_of_capital(df_dict, *args):
    if not df_dict:
        raise PreventUpdate
    try:
        df_dict_value = list(df_dict.values())[0]
        year0_dict = df_dict_value['fin_report_dict'][-1]
        equity_market_value = get_number_from_string(year0_dict['Shares Outstanding']) * df_dict_value['stats_dict']['lastprice'] /1e6
        beta = df_dict_value['stats_dict']['beta'] or 1
        debt_book_value, interest_expense_debt, average_maturity, pretax_cost_of_debt, convertible_debt_book_value, \
            convertible_market_value, convertible_debt_portion_market_value, preferred_num_shares, preferred_price_pershare, preferred_dividend_pershare, debt_value_op_leases, \
            erp, tax_rate, riskfree_rate, terminal_growth_eq_riskfree_rate, terminal_growth_rate, \
            live_analysis_mode, snapshot_uuid = args

        ticker = list(df_dict.keys())[0]
        dcf_store_dict = db.get(ticker+'-'+snapshot_uuid)
        safe_get_coc = json.loads(dcf_store_dict).get(ticker).get('cost-of-cap.value') if dcf_store_dict else None
        if 1 in live_analysis_mode or not safe_get_coc:
            pretax_cost_of_debt /= 100  # convert to %
            convertible_debt_portion_market_value /= 100

            # =B19*(1-(1+B25)^(-B20))/B25+B18/(1+B25)^B20
            debt_market_value = (interest_expense_debt * (1-(1+pretax_cost_of_debt) ** (-average_maturity)) / pretax_cost_of_debt) + (debt_book_value / ((1+pretax_cost_of_debt) ** average_maturity))
            convertible_market_value = (interest_expense_debt * (1-(1+pretax_cost_of_debt) ** (-average_maturity)) / pretax_cost_of_debt) + (convertible_debt_book_value / ((1+pretax_cost_of_debt) ** average_maturity))
            convertible_equity_portion_market_value = convertible_market_value * (1 - convertible_debt_portion_market_value)
            # TODO: Why Convertible Equity not used in CoC?
            total_debt = debt_market_value + convertible_debt_portion_market_value + debt_value_op_leases

            cap_structure_list = [equity_market_value, preferred_num_shares * preferred_price_pershare, total_debt]
            total_capital = sum(cap_structure_list)
            wcc = [c/total_capital for c in cap_structure_list]
            coc = [riskfree_rate + (beta * erp), 
                    100*preferred_dividend_pershare/preferred_price_pershare, 
                    100*pretax_cost_of_debt * (1-tax_rate/100)]
            # Use 5 basis points over the Terminal Growth rate as Minimum CoC
            min_coc = 0.05 + (riskfree_rate if terminal_growth_eq_riskfree_rate else terminal_growth_rate)

            return [max(sum([wcc[c]*rate for c, rate in enumerate(coc)]), min_coc)]
        else:
            return [safe_get_coc]
    except Exception as e:
        logger.exception(e)
        raise PreventUpdate

@app.callback([Output('terminal-growth-rate', 'disabled')],
[Input('override-default-assumptions', 'value')])
def override_assumptions(ovr_flag):
    return [1 in ovr_flag]

