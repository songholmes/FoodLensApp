#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 24 19:42:56 2021

@author: songyang
"""

import dash
from dash import Dash, dcc, html, dash_table, Input, Output, State, callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_pivottable
from dash import html
import base64
import pandas as pd
import base64, io, uuid


def datdash(df, x=list()):
    x = df.values.tolist()
    x.insert(0, list(df.columns))
    return x

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return df

layout = dbc.Card(
    [
        dbc.CardHeader('Pivot Table Plugin'),
        dbc.CardBody(
            [
                dbc.NavLink("Reference Link", href="https://community.plotly.com/t/dash-pivottable-released/43333",
                            active="exact",
                            external_link=True,
                            target='_blank'),
                html.Hr(),
                dcc.Upload(id='upload-table-file', children = html.Button('Upload a File'), multiple=False),
                html.Hr(),
                html.Div(id='pivot-table-content', className="p-2 overflow-auto")
            ]

        )
    ]
)


def register_callback(app):
    @callback(Output('pivot-table-content', 'children'),
              Input('upload-table-file', 'contents'),
              State('upload-table-file', 'filename'))
    def update_output(contents, filename):

        # No upload yet → do nothing
        if contents is None:
            list_like_df = [
                ['Animal', 'Count', 'Location'],
                ['Zebra', 5, 'SF Zoo'],
                ['Tiger', 3, 'SF Zoo'],
                ['Zebra', 2, 'LA Zoo'],
                ['Tiger', 4, 'LA Zoo'],
            ]
        else:
            df = parse_contents(contents, filename)
            list_like_df = datdash(df)

        # New key/id every call forces React remount (work‑around for bug #10)
        pivot_table = dash_pivottable.PivotTable(
            id=f'pivot-{uuid.uuid4()}',
            data=list_like_df
        )
        return [pivot_table]


if __name__ == '__main__':
    FA = "https://use.fontawesome.com/releases/v5.12.1/css/all.css"
    app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, FA])
    app.layout = layout
    register_callback(app)
    app.run_server(debug=False, port=8888)
