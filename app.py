import os
import logging
import flask
from flask_caching import Cache
import dash
import dash_bootstrap_components as dbc
# from dash_extensions.enrich import Dash, FileSystemStore, ServersideOutputTransform, DashTransformer
import redis
from dotenv import load_dotenv
load_dotenv()

console_handler = logging.StreamHandler(flask.logging.wsgi_errors_stream)
console_handler.setLevel(logging.ERROR)
logging.basicConfig(format='%(asctime)s: [%(levelname)-8s] in %(module)s: %(message)s',
                datefmt='%Y-%m-%d_%I:%M:%S_%p',
                level=logging.INFO,
                handlers=[console_handler,
                    logging.FileHandler(os.path.expandvars('./app_DCFoutput.log'), mode='w')
                ])

#instantiate dash app server using flask for easier hosting
server = flask.Flask(__name__)
app = dash.Dash(__name__, server = server, 
    meta_tags=[{ "content": "width=device-width"}], 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
logger = app.logger # use Flask's app.logger with above added handlers in basicConfig

# fs = FileSystemStore(cache_dir="tmp")
# sot = ServersideOutputTransform(backend=fs)
# app = DashTransformer(__name__, server = server, 
#     transforms=[sot],
#     meta_tags=[{ "content": "width=device-width"}], 
#     external_stylesheets=[dbc.themes.BOOTSTRAP],
#     )

app.title = 'Equity Valuation Analysis'
# used for dynamic callbacks
app.config.suppress_callback_exceptions = True

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'app',
    'CACHE_THRESHOLD': 1000
})

cache_redis = Cache(app.server, config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379'),
})

db = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))