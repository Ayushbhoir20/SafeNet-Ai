# SafeNet AI - Project Structure

This document describes the organized project structure with proper separation of frontend and backend components.

## 📁 Directory Structure

```
SafeNet AI/
│
├── 📂 backend/                      # Backend Python application
│   ├── 📂 dataset/                  # Training datasets
│   ├── 📂 model/                    # Trained ML models
│   │   ├── best_model.pkl           # Best performing model
│   │   ├── scaler.pkl               # Feature scaler
│   │   ├── model_metadata.pkl       # Model metrics
│   │   └── confusion_matrices.png   # Visualization
│   ├── 📂 notebooks/                # Jupyter notebooks (if any)
│   │
│   ├── app.py                       # Main Flask application
│   ├── auth.py                      # Authentication module
│   ├── blacklist_checker.py         # External blacklist checking
│   ├── content_analyzer.py          # Content analysis module
│   ├── credit_manager.py            # Credit management
│   ├── credit_system.py             # Credit system logic
│   ├── db.py                        # Database operations
│   ├── feature_extraction.py        # URL feature extraction
│   ├── pricing_config.py            # Pricing configuration
│   ├── report_generator.py          # Report generation
│   ├── stripe_config.py             # Stripe payment config
│   ├── stripe_webhooks.py           # Stripe webhook handlers
│   ├── tiered_detection.py          # Tiered detection engine
│   ├── train_model.py               # Model training script
│   ├── user_plan_helper.py          # User plan utilities
│   ├── word_generator.py            # Word generation utilities
│   ├── sample_report.docx           # Sample report (DOCX)
│   └── sample_report.pdf            # Sample report (PDF)
│
├── 📂 frontend/                     # Frontend web application
│   ├── 📂 static/                   # Static assets
│   │   ├── 📂 css/                  # Stylesheets
│   │   │   ├── admin.css            # Admin dashboard styles
│   │   │   ├── chatbot.css          # Chatbot styles
│   │   │   ├── dashboard.css        # Dashboard styles
│   │   │   ├── home.css             # Home page styles
│   │   │   ├── legal.css            # Legal pages styles
│   │   │   └── style.css            # Global styles
│   │   │
│   │   ├── 📂 images/               # Image assets
│   │   │   ├── brian_krebs.jpg
│   │   │   ├── dave_jevans.jpg
│   │   │   └── troy_hunt.jpg
│   │   │
│   │   ├── 📂 js/                   # JavaScript files
│   │   │   ├── chatbot.js           # Chatbot functionality
│   │   │   ├── global-shortcuts.js  # Global keyboard shortcuts
│   │   │   ├── home.js              # Home page scripts
│   │   │   ├── legal.js             # Legal pages scripts
│   │   │   ├── login.js             # Login page scripts
│   │   │   ├── register.js          # Registration scripts
│   │   │   └── script.js            # Global scripts
│   │   │
│   │   ├── favicon.ico              # Favicon (ICO)
│   │   ├── favicon.png              # Favicon (PNG)
│   │   └── favicon.svg              # Favicon (SVG)
│   │
│   ├── 📂 templates/                # HTML templates
│   │   ├── 📂 admin/                # Admin pages
│   │   │   ├── dashboard.html       # Admin dashboard
│   │   │   ├── messages.html        # Admin messages
│   │   │   ├── sales.html           # Sales analytics
│   │   │   └── users.html           # User management
│   │   │
│   │   ├── 📂 partials/             # Reusable template parts
│   │   │   └── footer.html          # Footer component
│   │   │
│   │   ├── 403.html                 # Forbidden page
│   │   ├── contact.html             # Contact page
│   │   ├── dashboard.html           # User dashboard
│   │   ├── disclaimer.html          # Disclaimer page
│   │   ├── faq.html                 # FAQ page
│   │   ├── home.html                # Home page
│   │   ├── login.html               # Login page
│   │   ├── payment_cancel.html      # Payment cancelled
│   │   ├── payment_success.html     # Payment success
│   │   ├── pricing.html             # Pricing page
│   │   ├── privacy.html             # Privacy policy
│   │   ├── register.html            # Registration page
│   │   ├── scan.html                # URL scan page
│   │   └── terms.html               # Terms of service
│   │
│   └── package.json                 # Frontend package config
│
├── 📂 .venv/                        # Python virtual environment
├── 📂 .vscode/                      # VS Code settings
├── 📂 .git/                         # Git repository
│
├── .env                             # Environment variables (NOT in git)
├── .gitignore                       # Git ignore rules
├── Procfile                         # Heroku deployment config
├── railway.json                     # Railway deployment config
├── render.yaml                      # Render deployment config
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
└── PROJECT_STRUCTURE.md             # This file

```

## 🎯 Key Points

### Backend (`/backend/`)
- All Python application code
- Flask app with proper path configuration to reference frontend
- ML models and training scripts
- Database operations and API endpoints
- Authentication and payment processing

### Frontend (`/frontend/`)
- All HTML templates
- CSS stylesheets
- JavaScript files
- Static assets (images, favicons)
- No build process required (vanilla JS/CSS)

### Root Level
- **Configuration files**: Deployment configs (Procfile, railway.json, render.yaml)
- **Dependencies**: requirements.txt for Python packages
- **Documentation**: README.md and this structure document
- **Environment**: .env for secrets and config (not in git)
- **Version control**: .git and .gitignore

## 🚀 Running the Application

### Development Mode

1. **Activate virtual environment:**
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the model (first time only):**
   ```bash
   python backend/train_model.py
   ```

4. **Run the application:**
   ```bash
   python backend/app.py
   ```

5. **Access the app:**
   Open browser to `http://localhost:5000`

### Production Deployment

The deployment configurations automatically handle the correct paths:

- **Procfile**: `gunicorn backend.app:app`
- **railway.json**: Uses `backend.app:app` and `backend/train_model.py`
- **render.yaml**: Uses `backend.app:app` and `backend/train_model.py`

## 📝 Notes

1. The Flask app in `backend/app.py` is configured to find templates and static files in the `frontend/` directory
2. All Python imports within backend use relative imports
3. The `__pycache__` directories are automatically ignored by git
4. The `.env` file contains sensitive credentials and is NOT committed to git
5. Virtual environment (`.venv`) is local only and not in git

## 🔧 Configuration

The backend Flask app uses the following path configuration:

```python
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(os.path.dirname(base_dir), 'frontend', 'templates')
static_dir = os.path.join(os.path.dirname(base_dir), 'frontend', 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
```

This allows the backend to properly serve frontend assets while maintaining clean separation.
