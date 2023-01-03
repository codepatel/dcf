import os
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from app import app, server
from layouts import navheader, tabheader, dcflayout, sectorlayout
import callbacks

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id="page-content", children=navheader)
])

@app.callback([Output('page-content', 'children'),
Output('nav-main', 'active'),
Output('nav-dcf', 'active'),
Output('nav-sector', 'active'),],
[Input('url', 'pathname')])
def display_page(pathname):
    if not pathname or pathname == '/': # Root "Main" page
        return navheader, True, False, False
    if '/apps/dcf' in pathname:
        return dcflayout, False, True, False
    elif pathname == '/apps/sector':
        return sectorlayout, False, False, True
    else:
        return html.H1("404!"), False, False, False

# @app.callback(Output("tab-content", "children"), [Input("tabs", "active_tab")])
# def switch_tab(at):
#     if at == "tab-dcf":
#         return dcflayout
#     elif at == "tab-sector":
#         return sectorlayout
#     return html.P("This shouldn't ever be displayed...")

if __name__ == '__main__':
    app.run_server(host=os.environ.get('HOST', '127.0.0.1'), debug=bool(os.environ.get('DEBUG', 'False')), use_reloader=False) # Turn off reloader if inside Jupyter or using interactive debugging
