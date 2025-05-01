# Food-Lens App

Plotly Dash web app that estimates calories & nutrition from food photos.

## Features
- Image upload → AI nutrition breakdown  
- Manual entry + batch uploads  
- Daily summaries & charts  
- Ready for local or Docker deployment

## Quick Start

### Local
```
git clone https://github.com/songholmes/FoodLensApp

cd food-lens-app

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements_prod.txt

python index.py           # http://localhost:3002
```

### Docker
```
docker build -t food-lens-app .

docker run -d -p 3002:3002 food-lens-app          # http://localhost:3002
```
### Directory Layout
```
app.py          – server setup/ login config
index.py        – Dash entry point
modules/        – Reusable utilities & callbacks
pages/          – Multi-page routing
uploads/        – Uploaded images (auto-created)
templates/      – Jinja overrides
data/           – Static reference data
Dockerfile      – Container build
requirements_*.txt
```

```
# Environment Vars (optional)
GOOGLE_CLIENT_ID  
GOOGLE_CLIENT_SECRET  For login username setup

OPENAI_API_KEY	LLM image analysis
```

### MIT License
