import flask
from flask_caching import Cache
import dash
import dash_bootstrap_components as dbc
from dotenv import load_dotenv
load_dotenv()

#instantiate dash app server using flask for easier hosting
server = flask.Flask(__name__)
app = dash.Dash(__name__, server = server, 
    meta_tags=[{ "content": "width=device-width"}], 
    external_stylesheets=[dbc.themes.BOOTSTRAP])
#used for dynamic callbacks
app.config.suppress_callback_exceptions = True

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'tmp',
    'CACHE_THRESHOLD': 100
})







