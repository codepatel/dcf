import os
from distutils.util import strtobool
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from app import app
from layouts import navheader, dcflayout, sectorlayout
import callbacks

if not os.path.exists('tmp'):   # use /tmp for logging and caching
    os.makedirs('tmp')

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/apps/dcf':
         return dcflayout
    elif pathname == '/apps/sector':
         return sectorlayout
    else:
        return navheader

if __name__ == '__main__':
    app.run_server(debug=bool(strtobool(os.environ.get('DEBUG', 'False'))), use_reloader=False) # Turn off reloader if inside Jupyter