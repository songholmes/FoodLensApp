import dash
from dash import dcc, html, Input, Output, State
from openai import OpenAI
import dash_bootstrap_components as dbc
import time
import os


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# 初始聊天记录
initial_messages = [{"role": "system", "content": "你是一个友好的助手。"}]

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("多轮对话 + 流式输出 Chatbot"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.Textarea(
            id='user-input',
            placeholder='请输入您的问题...',
            style={'width': '100%', 'height': 150}
        ), width=12)
    ]),
    dbc.Row([
        dbc.Col(dbc.Button('发送', id='submit-btn', color='primary', className='mt-2'), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.Div(id='chat-history', style={'whiteSpace': 'pre-wrap', 'marginTop': '20px'}), width=12)
    ]),
    # 隐藏存储聊天记录
    dcc.Store(id='chat-store', data=initial_messages)
], fluid=True)


@app.callback(
    Output('chat-history', 'children'),
    Output('chat-store', 'data'),
    Input('submit-btn', 'n_clicks'),
    State('user-input', 'value'),
    State('chat-store', 'data'),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_input, chat_history):
    if not user_input:
        return dash.no_update, dash.no_update

    # 更新聊天记录
    chat_history.append({"role": "user", "content": user_input})
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
    )
    # 模拟流式输出（用实际生产流式的话，建议用 websocket 或服务器推送）
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=chat_history,
        stream=True
    )

    reply_content = ""
    for chunk in response:
        if 'choices' in chunk and chunk['choices'][0]['delta'].get('content'):
            reply_content += chunk['choices'][0]['delta']['content']
            # 可选：如果要看到「流式效果」，你可以用 websocket 实现
            time.sleep(0.02)  # 人为延时模拟流式，真实生产用别的方法

    chat_history.append({"role": "assistant", "content": reply_content})

    # 格式化聊天记录展示
    formatted_chat = ""
    for msg in chat_history:
        if msg['role'] == 'user':
            formatted_chat += f"🧑 你: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            formatted_chat += f"🤖 AI: {msg['content']}\n"
    return formatted_chat, chat_history


if __name__ == '__main__':
    app.run_server(debug=True)
