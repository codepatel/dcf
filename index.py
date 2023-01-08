import os
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

from app import app, server
from layouts import sidebar, content, dcflayout, sectorlayout, legallayout
import callbacks

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    sidebar, content
])

@app.callback(Output('page-content', 'children'),
[Input('url', 'pathname')])
def render_page_content(pathname):
    if not pathname or pathname == '/': # Root "Main" page
        return html.P("Welcome Investor to the home page!")
    if '/apps/dcf' in pathname:
        return dcflayout
    elif pathname == '/apps/sector':
        return sectorlayout
    elif pathname == '/legal':
        return legallayout
    else: # If the user tries to reach a different page, return a 404 message
        return html.Div(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ],
        className="p-3 bg-light rounded-3",
        )

if __name__ == '__main__':
    app.run_server(host=os.environ.get('HOST', '127.0.0.1'), debug=bool(os.environ.get('DEBUG', 'False')), use_reloader=False) # Turn off reloader if inside Jupyter or using interactive debugging
