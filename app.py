import os
import flask
from flask_caching import Cache
import dash
import dash_bootstrap_components as dbc
# from dash_extensions.enrich import Dash, FileSystemStore, ServersideOutputTransform, DashTransformer
from dotenv import load_dotenv
load_dotenv()

#instantiate dash app server using flask for easier hosting
server = flask.Flask(__name__)
app = dash.Dash(__name__, server = server, 
    meta_tags=[{ "content": "width=device-width"}], 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    )

# fs = FileSystemStore(cache_dir="tmp")
# sot = ServersideOutputTransform(backend=fs)
# app = DashTransformer(__name__, server = server, 
#     transforms=[sot],
#     meta_tags=[{ "content": "width=device-width"}], 
#     external_stylesheets=[dbc.themes.BOOTSTRAP],
#     )

app.title = 'Equity Valuation Analysis'
#used for dynamic callbacks
app.config.suppress_callback_exceptions = True

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'tmp',
    # 'CACHE_TYPE': 'redis',
    # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    'CACHE_THRESHOLD': 1000
})







