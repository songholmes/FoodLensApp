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

cd FoodLensApp

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements_prod.txt

python index.py           # http://localhost:3002
```

### Prepare your .env

Google API Credentials: (Optional)<br>
* Used to log Google User Name, if not provided, it will use dummy user name
* Note: Even if valid Google credentials are provided, users may not be able to access the web app via a raw server IP address. This is because Google OAuth does not support IP addresses as redirect URIs—only localhost (127.0.0.1) or an HTTPS-enabled hostname is allowed.
```
# (Optional)  
GOOGLE_CLIENT_ID  
GOOGLE_CLIENT_SECRET  For login username setup
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


### Docker
```
docker build -t food-lens-app .

docker run -d -p 3002:3002 food-lens-app          # http://localhost:3002

# Or docker volumn mount with host disk: 
## docker run -v $(pwd)/data:/FoodLens/data -d -p 3002:3002 food-lens-app
```

### MIT License
