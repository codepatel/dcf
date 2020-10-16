#### About this App ####
- [Inspired by Professor Aswath Damodaran's teachings and Mission](http://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm)
- [Prof. Damodaran's Data Sources](http://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html)
- [Prof. Damodaran's Valuation Tools Webcast](https://www.youtube.com/watch?v=F9GfXJ-IrSA)
- [Prof. Damodaran's Valuation Spreadsheet Download link](http://www.stern.nyu.edu/~adamodar/pc/fcffsimpleginzuCorona.xlsx)
- The Intrinsic Value Calculation here is not as rigorous as the spreadsheet linked above and probably over-simplified in the present version of this app. As it evolves, the App will include more features for completeness over newer releases.

##### *Assumptions:* #####
1. Only non-financial companies (neither banks nor insurance companies)
2. NOLs are not accounted for in DCF valuation (to be improved in future release)
3. Cost of Capital is fixed for the timeline of valuation and not linked to the Cost of Capital worksheet and the Country Equity Risk Premium look-up (to be improved in future release and linked to source CSV if available)
4. Probability of failure for the firm assumes proceeds in case of bankruptcy are 50 cents on the $ of Present Value.

#### How to setup this App locally ####
1. `>> git clone git@github.com:codepatel/dcf.git`
2. `>> cd dcf`
3. `>> pip3 install -r requirements.txt` or 
    - If you use a virtual environment such as pipenv: `>> pipenv run pip install -r requirements.txt`
4. [Install Redis Server](https://redis.io/) - an in-memory data structure store, used as a database, cache and message broker.
    - [Brew Install Redis on Mac](https://gist.github.com/tomysmile/1b8a321e7c58499ef9f9441b2faa0aa8)
    - [For Linux: Installing Redis From Source](https://realpython.com/python-redis/#installing-redis-from-source)
    - [For Windows - Memurai (a fork of Redis)](https://www.memurai.com/get-memurai)
5. Create a .env file with following env variables defined:
   ```
    DEBUG = True
    FLASK_ENV = development
    REDIS_URL = redis://localhost:6379
    # IEX env settings: Use one of the two options below for TEST (Scrambled data) or LIVE (Real data)
    IEX_API_VERSION = iexcloud-sandbox or iexcloud-v1
    IEX_CLOUD_APIURL = https://sandbox.iexapis.com/stable/ or https://cloud.iexapis.com/stable/
    IEX_TOKEN = <Your TEST-SANDBOX or LIVE-CLOUD Public API Token>
    IEX_CLOUD_APISSEURL = https://sandbox-sse.iexapis.com/stable/ or https://cloud-sse.iexapis.com/stable/
    ```
    *Note: If you don't have an IEX Account, get started now with a Free Account by clicking this referral link:* [IEX Cloud is the easiest way to use financial data!](https://iexcloud.io/s/b47b5006)
6. `>> python index.py`  
    You can expect to see a command-line output like:
    ```
    Dash is running on http://127.0.0.1:8050/

    * Serving Flask app "app" (lazy loading)
    * Environment: development
    * Debug mode: on
    ```
7. Point your browser to: http://localhost:8050/apps/dcf/AAPL to get started.
8. Validate your analysis with others or your future self by clicking "Save Snapshot", use the Snapshot Link to Bookmark and share with others or look it up in the near or distant future.
