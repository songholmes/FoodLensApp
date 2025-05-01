import random
import string
import io
import base64
from PIL import Image, ImageDraw, ImageFont

from flask import Flask, send_file, session, request
import dash
from dash import html, dcc, Input, Output, State

# ========= Flask Setup =========
server = Flask(__name__)
server.secret_key = 'your-secret-key'  # Required for session

# ========= Dash Setup =========
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "Dash CAPTCHA Demo"

# ========= CAPTCHA Generation Function =========
def generate_captcha_text(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text):
    img = Image.new('RGB', (130, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Optional: Use your own font path
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except IOError:
        font = ImageFont.load_default()

    draw.text((10, 5), text, font=font, fill=(0, 0, 0))

    # Add noise
    for _ in range(30):
        x = random.randint(0, 130)
        y = random.randint(0, 40)
        draw.point((x, y), fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ========= Flask Route for CAPTCHA Image =========
@server.route('/captcha_image')
def serve_captcha():
    captcha_text = generate_captcha_text()
    session['captcha'] = captcha_text
    buf = generate_captcha_image(captcha_text)
    return send_file(buf, mimetype='image/png')

# ========= Dash Layout =========
app.layout = html.Div([
    html.H3("请输入下方图片中的验证码"),
    html.Img(src="/captcha_image", id="captcha-image", style={"margin": "10px 0"}),
    html.Button("刷新验证码", id="refresh-btn", n_clicks=0),
    dcc.Input(id='captcha-input', type='text', placeholder='输入验证码', style={'marginRight': '10px'}),
    html.Button("提交", id="submit-btn", n_clicks=0),
    html.Div(id='captcha-result', style={"marginTop": "20px", "color": "red"})
])

# ========= Refresh CAPTCHA on Button Click =========
@app.callback(
    Output('captcha-image', 'src'),
    Input('refresh-btn', 'n_clicks')
)
def refresh_captcha(n_clicks):
    return f"/captcha_image?rand={random.randint(0,100000)}"  # prevent caching

# ========= Validate CAPTCHA =========
@app.callback(
    Output('captcha-result', 'children'),
    Input('submit-btn', 'n_clicks'),
    State('captcha-input', 'value')
)
def validate_captcha(n_clicks, user_input):
    if n_clicks > 0:
        correct = session.get('captcha', '').strip().upper()
        if not user_input:
            return "请输入验证码"
        elif user_input.strip().upper() == correct:
            return "验证码正确 ✅"
        else:
            return "验证码错误 ❌，请重试"
    return ""

# ========= Run =========
if __name__ == '__main__':
    app.run_server(debug=True)
