
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output, State
import dateutil.relativedelta
from datetime import date
from app import app
from __init__ import DEFAULT_TICKER

def make_table(id, dataframe, lineHeight = '17px', page_size = 5):
    return   dash_table.DataTable(
        id=id,
        css=[{'selector': '.row', 'rule': 'margin: 0'}],
        columns=[
            {"name": i, "id": i} for i in dataframe.columns
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'},
            style_cell={'textAlign': 'left'},
            style_data={
                'whiteSpace': 'normal',
                'height': 'auto',
                'lineHeight': lineHeight
            },
        # style_table = {'width':300},
        style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
        style_cell_conditional=[
            {'if': {'column_id': 'title'},
            'width': '130px'},
            {'if': {'column_id': 'post'},
            'width': '500px'},
            {'if': {'column_id': 'datetime'},
            'width': '130px'},
            {'if': {'column_id': 'text'},
            'width': '500px'}],
        page_current=0,
        page_size=page_size,
        page_action='custom',
        filter_action='custom',
        filter_query='',
        sort_action='custom',
        sort_mode='multi',
        sort_by=[],
        data=dataframe.to_dict('records')
    )

def make_card(alert_message, color, cardbody, style_dict = None):
    return  dbc.Card([
        dbc.Alert(alert_message, color=color),
        dbc.CardBody(cardbody)
        ], style = style_dict
    )#end card

def ticker_inputs(inputID, pickerID, MONTH_CUTTOFF):
    
    currentDate = date.today() 
    pastDate = currentDate - dateutil.relativedelta.relativedelta(months=MONTH_CUTTOFF)
    
    return html.Div([
        dbc.Input(id = inputID, type="text", placeholder="Enter Ticker, press Enter", value=DEFAULT_TICKER, debounce=True, disabled=True), 
        html.P(" "), 
        # dcc.DatePickerRange(
        # id = pickerID,
        # min_date_allowed=pastDate,
        # max_date_allowed=currentDate,
        # #initial_visible_month=dt(2017, 8, 5),
        # start_date = pastDate,
        # end_date = currentDate
        # )
    ])

def make_item(button, cardbody, i):
    # we use this function to make the example items to avoid code duplication
    return dbc.Card([
        dbc.CardHeader(
            html.H2(
                dbc.Button(
                    button,
                    color="link",
                    id=f"group-{i}-toggle",
                ))
        ),
        dbc.Collapse(
            dbc.CardBody(cardbody),
            id=f"collapse-{i}",
        )
    ])

@app.callback([Output('social-share', 'children')],
[Input('url', 'href')])
def make_social_media_share(location):
    # got these buttons from simplesharebuttons.com, Yolandi Vi$$er
    return [dbc.CardGroup([
        dbc.Card([ # Facebook
            html.A(href=f'http://www.facebook.com/sharer.php?u={location}', target='_blank',
            children=dbc.CardImg(
            src='/assets/images/MiniFB.png',
            alt='Share with Facebook',
            title='Share with Facebook',
            style={'width':50, 'height':50}
            )),
        ]),
        dbc.Card([ # LinkedIn
            html.A(href=f'http://www.linkedin.com/shareArticle?mini=true&url={location}', target='_blank',
            children=dbc.CardImg(
            src='/assets/images/MiniLinkedIn.png',
            alt='Share with LinkedIn',
            title='Share with LinkedIn',
            style={'width':50, 'height':50}
            )),   
        ]),
        dbc.Card([ # Twitter
            html.A(href=f'http://twitter.com/share?url={location}&text=Stock_Analysis&hashtags=StockAnalysis', target='_blank',
            children=dbc.CardImg(
            src='/assets/images/MiniTwitter.png',
            alt='Tweet this!',
            title='Tweet this!',
            style={'width':50, 'height':50}
            )),
        ]), # , style={"width": "5rem"}
        dbc.Card([ # Pinterest
            html.A(href=f'https://pinterest.com/pin/create/button/?url={location}&media=StockAnalysis&description=StockAnalysis', target='_blank',
            children=dbc.CardImg(
            src='/assets/images/MiniPinterest.png',
            alt='Pin It!',
            title='Pin It!',
            style={'width':50, 'height':50}
            )),            
        ]),
        dbc.Card([ # Email
            html.A(href=f'mailto:?Subject=Stock Analysis Web App&Body=I saw this and wanted to share it with you: {location}', target='_blank',
            children=dbc.CardImg(
            src='/assets/images/MiniEmail.png',
            alt='Email link!',
            title='Email link!',
            style={'width':50, 'height':50}
            )),            
        ]),
        #dbc.Card([])    # empty card at end as spacer
    ])]

def replace_str_element_w_dash_component(str_with_newlines, sep_str='\n', repl_dash_component=html.Br()):
    str_list = str_with_newlines.split(sep_str)
    nested_list = [[html.P(s), repl_dash_component] for s in str_list]
    return [item for sublist in nested_list for item in sublist]