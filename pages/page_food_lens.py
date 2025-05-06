#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 22 20:42:24 2021

@author: songyang
"""

import os
import uuid
# Ignore warnings
import warnings
from datetime import datetime, date
from pathlib import Path
import json

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ======================== General Import ====================================
import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, dcc, Input, Output, State, ctx, no_update
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from dash.exceptions import PreventUpdate
from .scripts.food_lens_functions import *
from .scripts.generate_graph import graph, get_llm

warnings.filterwarnings("ignore")
tz = ZoneInfo("Asia/Singapore")

# dummy image with 32x32
dummy_test_b64_img = ("iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAKElEQVR4nO3NMQE"
                      "AAAjDMMC/ZzDBvlRA01vZJvwHAAAAAAAAAAAAbx2jxAE/i2AjOgAAAABJRU5ErkJggg==")
test_img_prompt = [
    {"role": "user", "content": [
        {"type": "text", "text": "What do you see in this image?"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{dummy_test_b64_img}"}}
    ]
     }
]



# %% ===========================================================================
# # UI Layout
# =============================================================================
tab0_subtab_0 = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Provider", id='provider-label', html_for="llm-provider-dpn"),
                        dcc.Dropdown(
                            id="llm-provider-dpn",
                            options=[{'label': m, 'value': m} for m in
                                     ['openai', 'azure', 'anthropic', 'gemini', 'vllm']],
                            placeholder="openai/ azure /vllm",
                        ),
                        dbc.Tooltip(
                            "Input the provider like: openai, azure, anthropic, gemini or vllm",
                            target="llm-provider-dpn",
                            placement='right'
                        ),
                    ],
                    width=4,
                    className="mb-3"
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Model Name", html_for="llm-model-name-input"),
                        dbc.Input(
                            id="llm-model-name-input",
                            placeholder="gpt-4o-mini/ meta-llama/Llama-3.2-1B-Instruct",
                        ),
                    ],
                    width=4,
                    className="mb-3"
                ),
                dbc.Col(
                    [
                        dbc.Label("API Key (Optional for vLLM)", html_for="llm-api-key-input"),
                        dbc.Input(
                            type="password",
                            id="llm-api-key-input",
                            placeholder="Enter the API key",
                        ),
                        dbc.Tooltip(
                            "Optional for vLLM",
                            target="llm-api-key-input",
                        ),
                    ],
                    width=4,
                    className="mb-3"
                ),
                dbc.Col(
                    [
                        dbc.Label("Base URL/ Endpoint", html_for="llm-model-url-input"),
                        dbc.Input(
                            id="llm-model-url-input",
                            placeholder="Enter the base url (openai, anthropic..) or endpoint(azure)",
                        ),
                    ],
                    width=4,
                    className="mb-3"
                ),
            ],
            className="g-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Azure Deployment (Optional)", html_for="llm-deployment-input"),
                        dbc.Input(
                            id="llm-deployment-input",
                            placeholder="Enter your Azure Deployment Name",
                        ),
                    ],
                    width=4,
                    className="mb-3"
                ),
                dbc.Col(
                    [
                        dbc.Label("Azure API Version (Optional)", html_for="llm-api-version-input"),
                        dbc.Input(
                            id="llm-api-version-input",
                            placeholder="like 2024-04-01-preview"
                        ),
                    ],
                    width=4,
                    className="mb-3"
                ),
            ],
            className="g-3",
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Button("Add", id="llm-credential-add-btn", n_clicks=0), width=1),
            ], justify='start'
        ),
        html.Br(),
        dbc.Row(
            [
                html.Div(id="model-credential-verification-results", className="mb-3"),]
        )
    ]
)

tab0_subtab_1 = dbc.Container(
    [
        dcc.Upload(
            id="llm-bulk-upload",
            children=dbc.Button("Upload JSON File", color="secondary"),
            multiple=False
        ),
        html.Div(id="bulk-upload-feedback", className="mt-3")
    ],
    fluid=True,
    class_name="p-3"
)

tab0 = [
        dbc.Card(
            [
                dbc.CardBody(
                        dbc.Tabs(
                            [
                                dbc.Tab(tab0_subtab_0, label='Single LLM Credential', tab_id='tab0-subtab-0'),
                                dbc.Tab(tab0_subtab_1, label='Bulk Upload (JSON)', tab_id='tab0-subtab-1'),
                            ],
                            id="llm-credential-tabs",
                            active_tab='tab0-subtab-0',
                            class_name="mb-5"
                        )
                )
            ],
            class_name="mb-4 shadow-sm"
        ),
        dbc.Card(
            [
                dbc.CardHeader("Select your LLM model to continue"),
                dbc.CardBody(
                    [
                        dbc.Row(
                            dbc.Col(
                                dcc.Dropdown(id="llm-credential-dpn", className="mb-2"),
                                md=6
                            )
                        ),
                        dbc.Row(
                            dbc.Col(
                                dbc.Button("Next", id="next-btn", color="success", size="lg",
                                           n_clicks=0, disabled=True),
                                class_name="d-grid gap-2 d-md-flex justify-content-md-end"
                            )
                        )
                    ]
                )
            ],
            class_name="shadow-sm"
        )
    ]

tab1 = [
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader('''Click the below button to upload food image to identify'''),
                        dbc.CardBody(
                            [
                                dcc.Store(id='graph-thread-id'),
                                dcc.Upload(id='upload-food-image',
                                           children=dbc.Button('Upload Food Image'),
                                           multiple=False
                                           ),
                                html.Hr(),
                                dbc.Row(id='food-image-upload'),
                                html.Hr(),
                                html.H5(children='Calculated Calorie', className="mb-3"),

                                dbc.Row(id='meal-setting-placeholder', children=[
                                    dbc.Col([
                                        dbc.Label("Set Meal for All Rows", html_for="meal-type-dropdown",
                                                  className="mb-1"),
                                        dcc.Dropdown(
                                            id='meal-type-dropdown',
                                            options=[{'label': m, 'value': m} for m in
                                                     ['Breakfast', 'Lunch', 'Dinner', 'Snack']],
                                            placeholder='Select a meal',
                                            clearable=True
                                        )
                                    ], width=3),

                                    dbc.Col([
                                        dbc.Label("Set Date for All Rows", html_for="meal-datepicker",
                                                  className="mb-1"),
                                        dcc.DatePickerSingle(
                                            id='meal-datepicker',
                                            date=datetime.now(tz).date(),
                                            style={"width": "100%"},
                                            display_format='YYYY-MM-DD'
                                        )
                                    ], width=6)
                                ]),

                                dbc.Row(dcc.Loading(
                                    id='upload-food-image-loading',
                                    type='circle',
                                    children=[html.Div(id='calorie-table-div'),
                                              html.Div(id="load-anchor", style={"display": "none"})]
                                )
                                ),
                                dcc.Store(id='calorie-table-data'),
                                dbc.Row(
                                    dbc.Col(
                                        dbc.Button('Write into Database?',
                                                   id='update_calorie_db_btn',
                                                   color='secondary', n_clicks=0,
                                                   class_name='mt-2', style={'display': 'none'}),
                                        width=2
                                    )
                                ),
                                dbc.Row(
                                    dcc.Loading(
                                        id='write-response-loading',
                                        type='circle',
                                        children=html.Div(id='upload-response-div')
                                    )
                                )
                            ]
                        )
                    ]

                ), width=12
            )
        ]
    ),
    html.Hr(),

]

tab2 = [
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader('User Information'),
                        dbc.CardBody(
                            [
                                html.H5(children='''About You: Generate Threshold for Plots''', className='mb-3'),
                                dbc.Row(
                                    [
                                        dbc.Col([dbc.Label('Age:', className='me-1'),
                                                 dcc.Input(id='age-input')], width=3),
                                        dbc.Col([dbc.Label('Weight:', className='me-1'),
                                                 dcc.Input(id='weight-input')], width=3),
                                        dbc.Col([dbc.Label('Height:', className='me-1'),
                                                 dcc.Input(id='height-input')], width=3),
                                    ]
                                ),
                            ]
                        )
                    ]

                ), width=12
            )
        ]
    ),
    html.Br(),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Analysis of Your Today's Diet"),
                        dbc.CardBody(
                            [
                                dcc.Graph(id='today-food-analysis-graph')
                            ]
                        )
                    ]

                ), width=12
            )
        ]
    ),
    html.Hr(),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Analysis of Your Past Diet"),
                        dbc.CardBody(
                            [
                                dbc.Row(children=[
                                    dbc.Col([
                                        dbc.Label("Metric to Check", html_for="plot-metric-type-dropdown",
                                                  className="mb-1"),
                                        dcc.Dropdown(
                                            id='plot-metric-type-dropdown',
                                            options=[{'label': m.replace('_g', '').title(), 'value': m} for m in
                                                     ['calories', 'carbs_g', 'protein_g', 'saturated_fat_g', 'unsaturated_fat_g']
                                                     ],
                                            value='calories',
                                            placeholder='Select a Metric to Plot',
                                            clearable=True
                                        )
                                    ], width=3),
                                    dbc.Col([
                                        dbc.Label("How many days to check", html_for="plot-metric-type-dropdown",
                                                  className="mb-1"),
                                        dbc.RadioItems(
                                            id="radios-past-days",
                                            className="btn-group",
                                            inputClassName="btn-check",
                                            labelClassName="btn btn-outline-primary",
                                            labelCheckedClassName="active",
                                            options=[
                                                {"label": "7 Days", "value": 7},
                                                {"label": "30 Days", "value": 30},
                                            ],
                                            value=7,
                                        ),
                                    ], width=3)
                                ]
                                        ),
                                dcc.Graph(id='past-food-analysis-graph')
                            ]
                        )
                    ]

                ), width=12
            )
        ]
    ),
    html.Hr(),

]

layout = dbc.Card(
    [
        dbc.CardHeader('Food Lens App'),
        dbc.CardBody(
            dbc.Tabs(
                [
                    dbc.Tab(label='Step 1: Load your LLM Model',
                            children=dbc.CardBody(tab0, class_name="mt-2"), tab_id='tab-0', id='tab0'),
                    dbc.Tab(label="Step 2: Food Nutrition Identification",
                            children=dbc.CardBody(tab1, class_name="mt-2"), tab_id="tab-1", id='tab1'),
                    dbc.Tab(label="Step 3: Analysis of Your Diet",
                            tab_id="tab-2", id='tab2'),
                ],
                id="food-card-tabs",
                active_tab="tab-0",

            )
        ),
        dcc.Store(id="upload-food-image-path"),
        dcc.Store(id="all-verify-llm-model-credentials", data={}),
        dcc.Store(id="select-llm-model", data=None)
    ]
)


# %% ===========================================================================
# # Callback Defined
# =============================================================================

def register_callback(app):
    import logging
    app.logger.setLevel(logging.DEBUG)

    @app.callback(
        Output("all-verify-llm-model-credentials", "data"),
        Output("model-credential-verification-results", "children"),
        Input("llm-credential-add-btn", "n_clicks"),
        State("all-verify-llm-model-credentials", "data"),
        State("llm-provider-dpn", "value"),
        State("llm-model-name-input", "value"),
        State("llm-api-key-input", "value"),
        State("llm-model-url-input", "value"),
        State("llm-deployment-input", "value"),
        State("llm-api-version-input", "value"),
        prevent_initial_call=True
    )
    def add_single_model_credentials(n_clicks, credential_dict,
                                     provider, model_name, api_key, model_url, deployment, api_version):
        if n_clicks is None or n_clicks <= 0:
            raise PreventUpdate()
        # Ensure we always have a mutable dict
        credential_dict = credential_dict or {}

        input_llm_cfg = {
            "provider": provider,  # Required: "openai", "azure", "anthropic", "gemini", or "vllm"
            "api_key": api_key,  # Required for all providers except "vllm"
            "model": model_name,
            "api_version": api_version,  # Only for "azure"
            "endpoint": model_url,  # Only for "azure"
            "deployment": deployment,  # Only for "azure"
            "base_url": model_url,
            "max_tokens": 10 # reduce cost for the test ping
        }
        try:
            provider_model_id = f"{input_llm_cfg.get('provider')}_{input_llm_cfg.get('model')}"
            test_llm = get_llm(with_struct_output=False, **input_llm_cfg)
            test_response = test_llm.invoke(test_img_prompt)
            input_llm_cfg.pop("max_tokens", None)
            credential_dict[provider_model_id] = input_llm_cfg

            test_res_div = [
                dbc.Row([
                    dbc.Col(html.H5(f'The added {provider_model_id}:')),
                    dbc.Col(html.Span(dbc.Badge('Pass', color='success', className="me-1 text-decoration-none")))
                ]),
            ]

        except Exception as e:
            # Remove the model, in case it already existed
            credential_dict.pop(provider_model_id, None)
            test_res_div = [
                dbc.Row([
                    dbc.Col(html.H5(f'The added {provider_model_id}:')),
                    dbc.Col(html.Span(dbc.Badge('Fail', color='danger', className="me-1 text-decoration-none")))
                ]),
                dbc.Row(dbc.Label(str(e)))]
            print("Your input model is incorrect")

        return credential_dict, test_res_div

    @app.callback(
        Output("select-llm-model", 'data'),
        Input("llm-credential-dpn", 'value')
    )
    def update_selected_llm(provide_model_id):
        return provide_model_id

    @app.callback(
        Output('tab1', 'disabled'),
        Output('next-btn', 'disabled'),
        Input("select-llm-model", 'data')
    )
    def enable_tab_btn(select_llm_model):
        if select_llm_model is not None:
            return False, False
        else:
            return True, True

    @app.callback(
        Output("llm-credential-dpn", "options"),
        Input("all-verify-llm-model-credentials", "data"),
        Input("food-card-tabs", "active_tab")
    )
    def load_model_dropdown_options(credential_dict, active_tab):
        # only update when Tab 0 is activated
        if active_tab != "tab-0":
            raise PreventUpdate()

        options_ = [{"label": k, "value": k} for k in credential_dict.keys()]

        return options_

    @app.callback(
        Output("food-card-tabs",'active_tab'),
        Input('next-btn', 'n_clicks'),
        State("select-llm-model", "data"),
        prevent_initial_call=True
    )
    def jump_to_step2(n_clicks, selected_model):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate()

        return 'tab-1'

    @app.callback(
        Output('tab2', "children"),
        [Input("food-card-tabs", "active_tab")]
    )
    def tab_content(active_tab):
        if active_tab == 'tab-2':
            return dbc.CardBody(tab2, class_name="mt-2")

    @app.callback(
        Output('meal-type-dropdown', 'value'),
        Output('meal-datepicker', 'date'),
        Input('meal-setting-placeholder', 'children')
    )
    def update_meal_setting(_):
        current_datetime_ = datetime.now(tz)
        return get_meal_time(current_datetime=current_datetime_), datetime.now(tz).date()

    @app.callback(Output('food-image-upload', 'children'),
                  Output('upload-food-image-path', 'data'),
                  Input('upload-food-image', 'contents'),
                  State('upload-food-image', 'filename'))
    def update_output(contents, image_file_name):
        if contents is None:
            raise PreventUpdate()

        if contents is not None:
            # Extract the image and downsample the longest side to 512 pix
            img_resize_, base64_resize_str_, raw_base64_bytes = process_upload_img(contents, b_crop_to_512=False)
            display_results = [
                dbc.Col(
                [
                    html.P(children=f"{image_file_name.split('.')[0][:10]}.{image_file_name.split('.')[1]}"),
                    html.Img(src=base64_resize_str_,
                             style={'max-width': '100%', 'max-height': '512px'}),
                ], width=5),
                dbc.Col([
                    html.P(children=f"Feedback your correctness on the results"),
                    dcc.Textarea(
                        id='user-feedback-input',
                        placeholder=(
                            "If you found the identified results are incorrect,\n"
                            "provide your feedback like: it is chicken rather than beef\n"
                            "or chicken is 200g rather than 100g."
                        ),
                        style={
                            'width': '100%',
                            'height': '300px',  # Control height to match roughly half the image
                            'resize': 'vertical',  # Optional: allow user to resize vertically
                            'marginBottom': '10px'  # Add space before button
                        }
                    ),
                    dbc.Button(
                        'Submit',
                        id='user-feedback-submit-btn',
                        color='primary',
                        n_clicks=0,
                        style={'width': '100%'}  # Button takes full width below textarea
                    )
                ], width=5)
            ]

            file_path = UPLOAD_DIR / f"{uuid.uuid4()}.png"
            file_path.write_bytes(base64.b64decode(raw_base64_bytes))

            return display_results, file_path.as_posix()

    @app.callback(Output('calorie-table-data', 'data'),
                  Output('update_calorie_db_btn', 'style'),
                  Output('graph-thread-id', 'data'),
                  Output("load-anchor", 'children'),
                  Input('upload-food-image-path', 'data'),
                  Input('all-verify-llm-model-credentials', 'data'),
                  Input('select-llm-model', 'data')
                  )
    def llm_identifier(food_image_path, credentials_dict, selected_llm_id):
        if (food_image_path is None) or (not credentials_dict) or (selected_llm_id is None):
            raise PreventUpdate()

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        # Input image to trigger the graph
        llm_cfg = credentials_dict[selected_llm_id]
        state = {"image_path": food_image_path, "llm_cfg": llm_cfg}
        graph.invoke(state, config=config, interrupt_before=['user_feedback'])

        # 拿最新结果
        response = graph.get_state(config).values["llm_output"]

        df_response = parse_response_to_dataframe(response)
        cur_datetime = datetime.now(tz)
        df_response['meal_date'] = cur_datetime.strftime("%Y-%m-%d")
        df_response['meal_type'] = get_meal_time(cur_datetime)

        return df_response.to_dict("records"), {'display': 'block'}, thread_id, "Loading Anchor"

    @app.callback(Output('calorie-table-data', 'data', allow_duplicate=True),
                  Output("load-anchor", 'children', allow_duplicate=True),
                  Input('user-feedback-submit-btn', 'n_clicks'),
                  State('user-feedback-input', 'value'),
                  State('graph-thread-id', 'data'),
                  State('all-verify-llm-model-credentials', 'data'),
                  State('select-llm-model', 'data'),
                  prevent_initial_call=True
                  )
    def user_feedback_llm_re_identify(n_clicks, user_feedback_input, thread_id,
                                      credentials_dict, selected_llm_id):
        if (not n_clicks) or (n_clicks == 0) or (not credentials_dict) or (selected_llm_id is None):
            # 没点按钮时，也要给 Dash 正确的返回
            return no_update, no_update
        config = {"configurable": {"thread_id": thread_id}}
        llm_cfg = credentials_dict[selected_llm_id]
        # 把用户反馈写入 state，再往前推进一步
        graph.update_state(config, {"feedback": user_feedback_input, "llm_cfg": llm_cfg})
        graph.invoke({}, config=config)  # 执行 user_feedback 节点

        response_fb = graph.get_state(config).values["llm_output"]
        df_response_fb = parse_response_to_dataframe(response_fb)
        cur_datetime = datetime.now(tz)
        df_response_fb['meal_date'] = cur_datetime.strftime("%Y-%m-%d")
        df_response_fb['meal_type'] = get_meal_time(cur_datetime)

        return df_response_fb.to_dict("records"), "Loading Anchor"

    @app.callback(Output('calorie-table-div', 'children'),
                  Input('calorie-table-data', 'data'),
                  )
    def render_calorie_table(calorie_identified_data):
        if calorie_identified_data is None:
            raise PreventUpdate()

        df_calorie_data = pd.DataFrame(calorie_identified_data)

        # Add Meal datetime, meal type and creation datetime
        columnDefs = []
        for c in df_calorie_data.columns:
            if c == 'timestamp':
                continue
            field_setting = {}
            field_setting['field'] = c
            field_setting['headerName'] = header_name_mapping[c]
            columnDefs.append(field_setting)

        response_grid = dag.AgGrid(
            id="calorie-table",
            rowData=df_calorie_data.to_dict("records"),
            columnDefs=columnDefs,
            dashGridOptions={
                "domLayout": "autoHeight",  # 小屏/手机常用
                "rowSelection": "multiple",  # 多选行示例
                "pagination": True,  # 分页示例
                "undoRedoCellEditing": True,
                "undoRedoCellEditingLimit": 10,
            },
            defaultColDef={"editable": True, "cellDataType": False},
            style={"width": "100%", "overflowX": "auto"}
        )

        return [response_grid]

    @app.callback(Output('calorie-table-data', 'data', allow_duplicate=True),
                  Input('calorie-table-data', 'data'),
                  Input('meal-type-dropdown', 'value'),
                  Input('meal-datepicker', 'date'),
                  prevent_initial_call=True
                  )
    def override_meal_info_by_user(calorie_data, new_meal_type, new_meal_date):

        if calorie_data is None:
            raise PreventUpdate()

        df_calorie_data = pd.DataFrame(calorie_data)

        # Add Meal datetime, meal type and creation datetime
        df_calorie_data['meal_type'] = new_meal_type
        df_calorie_data['meal_date'] = new_meal_date
        timestamp = datetime.now(tz).strftime('%H%M%S')
        df_calorie_data['timestamp'] = df_calorie_data.apply(lambda x: f"{x['meal_date']}|{timestamp}|{x['food_item']}",
                                                             axis=1)

        return df_calorie_data.to_dict("records")

    @app.callback(Output('upload-response-div', 'children'),
                  Input('update_calorie_db_btn', 'n_clicks'),
                  State('calorie-table-data', 'data'),
                  State("username", "children"),
                  State('upload-food-image-path', 'data')
                  )
    def upload_calorie_data_to_db(n_clicks, calorie_data, username, upload_img_path):
        if calorie_data is None:
            raise PreventUpdate()
        if n_clicks > 0:
            calorie_data_df = pd.DataFrame.from_records(calorie_data)
            write_record_to_db('foodlens_records_dev', username, calorie_data_df)
            Path(upload_img_path).unlink(missing_ok=True) # If ok to upload to DB, then remove image
            return 'Upload Calorie Data Successfully'


    @app.callback(Output('today-food-analysis-graph', 'figure'),
                  Input("username", "children")
                      )
    def plot_today_food_analysis(username):
        end_time = datetime.now(tz).date()
        start_time = end_time

        df_today = query_user_records_to_dataframe(
            table_name='foodlens-records-dev',
            user_id=username,
            start_datetime=start_time,
            end_datetime=end_time
        )
        if df_today.empty:
            raise PreventUpdate()
        else:
            app.logger.info(f"df_today: {df_today}")
            df_today_latest = get_latest_creation_records(df_today)
            app.logger.info(f"df_today_latest: {df_today_latest}")
            app.logger.info("df_today_latest.dtypes:\n%s", df_today_latest.dtypes)
            app.logger.info("protein_g:\n%s", df_today_latest['protein_g'].tolist())
            fig_today = get_plot_today_records_fig(df_today_latest)

            return fig_today
    @app.callback(
        Output('past-food-analysis-graph','figure'),
        Input('username', 'children'),
        Input('plot-metric-type-dropdown', 'value'),
        Input('radios-past-days', 'value'),
    )
    def update_date_range(username, metric, days):
        today = datetime.now(tz).date()
        start_date = today - timedelta(days=days)

        df_past = query_user_records_to_dataframe(
            table_name='foodlens-records-dev',
            user_id=username,
            start_datetime=start_date,
            end_datetime=today
        )

        df_past_latest = get_latest_creation_records(df_past)

        fig_past = get_plot_range_records_fig(df_past_latest, metric=metric)
        return fig_past

# %% Main Script

if __name__ == '__main__':
    FA = "https://use.fontawesome.com/releases/v5.12.1/css/all.css"
    app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, FA],
                    suppress_callback_exceptions=True)

    app.layout = layout
    register_callback(app)

    app.run_server(debug=True, port=3000)
