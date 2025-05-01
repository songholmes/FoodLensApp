#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 22 20:37:54 2021

@author: songyang
"""
import os
import sys

sys.path.insert(0, './pages/scripts')

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
import base64
import numpy as np
import pandas as pd
from app import app, register_auth_app, server

from pages import (
    page_plot_w_input, page_table_actions, page_dym_callback, page_pivottable, page_input_output,
    page_dbc, page_todo_practice, page_table_edit_db, page_food_lens
)

# =========== NAVBAR ===========
LOGO_IMG_FILE = r"./assets/img/dash_logo.png"
LOGO_IMG = base64.b64encode(open(LOGO_IMG_FILE, 'rb').read())

search_bar = dbc.Row(
    [
        dbc.Col(dbc.Input(type="search", placeholder="Search")),
        dbc.Col(
            dbc.Button(
                html.I(className="fas fa-search"),
                color="secondary", className="ms-2", n_clicks=0
            ),
            width="auto",
        ),
    ],
    className="g-0 ms-auto flex-nowrap mt-3 mt-md-0",
    align="center",
)



# user info
user_info = dbc.Row(
    [
        dcc.Store(id='username-url', data=''),
        dbc.Col(html.I(className='fas fa-user'), width='auto'),
        dbc.Col(html.Label(children='User Name', id='username', className='mt-1'), width='auto'),
    ],
    className='d-flex align-items-center flex-nowrap text-light g-2'
)

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    # Left LOGO
                    dbc.Col(html.Img(src='data:image/png;base64,{}'.format(LOGO_IMG.decode()), height='35px'),
                            width="auto"),
                    dbc.Col(dbc.NavbarBrand('Dash'), width="auto"),
                ],
                align="center",
                className="g-3",
            ),

            # Right Search bar + Username
            dbc.Row(
                [
                    dbc.Col(search_bar, className='me-1', width=7),
                    dbc.Col(user_info, width='auto')
                ],
                className="ms-auto d-flex align-items-center",
                align="center",
            ),
        ],
        fluid=True
    ),
    color='#0091da',
    dark=True,
    sticky="top",
)

# =========== SIDEBAR (Allow to Fold) ===========
sidebar_content = dbc.Collapse(
    id="collapse_sidebar",
    is_open=True,  # Default Extend
    children=[
        dbc.Nav(
            [
                dbc.NavLink('Food Lens', href="/page-food-lens", active="exact"),
                dbc.NavLink("Tableau-like Feature", href="/page-5", active="exact"),
                dbc.NavLink("Data I/O ", href="/page-IO", active="exact"),
                dbc.NavLink('To-Do List Feature', href="/page-todo-practice", active="exact"),
                dbc.NavLink('Table Edit w DB Feature', href="/page-table-edit-db", active="exact"),

            ],
            vertical=True,
            pills=True,
        ),
    ]
)

# Use one layer Div contain a toggle button + fold sidebar
sidebar = html.Div(
    [
        dbc.Button(
            "☰", color="secondary", outline=True,
            id="btn_sidebar_toggle",
            style={"margin-bottom": "1rem"}
        ),
        sidebar_content
    ],
    id="sidebar",
    style={"background-color": "#f8f9fa", "padding": "1rem"}  # 可自行调整
)

# =========== Main Contents ===========

content = html.Div(
    id="page-content",
    style={"padding": "1rem"}
)

# =========== Layout Main Body ===========

# Navbar + (Sidebar + Content) + Footer
# Use dbc.Container + dbc.Row/Col to control the response
# fluid=True make container suitable the screen width automatically
app.layout = html.Div([
    dcc.Location(id="url"),  # Monitor the browser url

    # Data Store
    html.Div(id='placeholder'),
    dcc.Store(id='data_source_1'),
    dcc.Store(id='db_movie_data'),
    dcc.Store(id='db_movie_data_updated'),
    dcc.Store(id='valid_access_res'),

    navbar,
    dbc.Container(
        fluid=True,
        children=[
            dbc.Row(
                [
                    dbc.Col(sidebar, xs=12, sm=12, md=3, lg=2),  # 侧边栏在小屏可以占满一行
                    dbc.Col(content, xs=12, sm=12, md=9, lg=10)  # 内容区
                ],
                className="g-2",  # gap
            ),
        ],
        style={"padding": "1rem"}
    ),
    html.Footer('© 2022 Song Holmes', className='text-center mt-4')
])


# =========== callbacks：sidebar fold ===========

@app.callback(
    Output("collapse_sidebar", "is_open"),
    [Input("btn_sidebar_toggle", "n_clicks")],
    [State("collapse_sidebar", "is_open")],
    prevent_initial_call=True
)
def toggle_sidebar(n_clicks, is_open):
    if not n_clicks:
        raise PreventUpdate
    return not is_open


# =========== Router/Page callback ===========

@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/" or pathname is None:
        return html.P("This is the content of the home page!")
    elif pathname == "/page-1":
        return page_plot_w_input.layout
    elif pathname == "/page-3":
        return page_table_actions.layout
    elif pathname == "/page-4":
        return page_dym_callback.layout
    elif pathname == "/page-5":
        return page_pivottable.layout
    elif pathname == "/page-IO":
        return page_input_output.layout
    elif pathname == "/page-dbc":
        return page_dbc.layout
    elif pathname == "/page-todo-practice":
        return page_todo_practice.layout
    elif pathname == "/page-table-edit-db":
        return page_table_edit_db.layout
    elif pathname == "/page-food-lens":
        return page_food_lens.layout
    elif pathname == "/logout":
        return dbc.Container([
            html.H1("Successfully Logout", className="text-danger")
        ])
    else:
        return dbc.Container(
            [
                html.H1("404: Not found", className="text-danger"),
                html.Hr(),
                html.P(f"The pathname {pathname} was not recognised..."),
            ],
            fluid=True,
            className="py-3",
        )


# Main Business Logic
@app.callback(
    Output('data_source_1', 'data'),
    Input('placeholder', 'children')
)
def data_transition(_):
    df = pd.DataFrame(data=np.array([[5, 3, 6],
                                     [4, 5, 6]]),
                      columns=['col1', 'col2', 'col3'])
    return df.to_json(date_format='iso', orient='split')

# %% Client Callback: to get the visitor username
# app.clientside_callback(
#     '''
# function Get(yourUrl){
#     var Httpreq = new XMLHttpRequest(); // a new request
#     Httpreq.open("GET", yourUrl, false);
#     Httpreq.withCredentials = true;
#     Httpreq.send(null);
#     return Httpreq.responseText.replaceAll('"', '');
#     }

#     ''',
#     Output('username','children'),
#     Input('username-url', 'data')
#     )

# Register all logical callback
page_plot_w_input.register_callback(app)
page_table_actions.register_callback(app)
page_dym_callback.register_callback(app)
page_pivottable.register_callback(app)
page_input_output.register_callback(app)
page_dbc.register_callback(app)
page_todo_practice.register_callback(app)
page_table_edit_db.register_callback(app)
page_food_lens.register_callback(app)

# Auth register
register_auth_app(app)

# =========== Suitable for mobile device ===========

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# =========== Start Server ===========
if __name__ == "__main__":
    # Official launched a more neat version for multi-page: https://dash.plotly.com/urls
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # If http test
    app.run_server(host='0.0.0.0', port=3002, debug=False)
