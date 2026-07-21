# 🚀 Vercel Deployment Guide for SafeNet AI

## ✅ Project Reorganization Complete

Your Flask application has been successfully reorganized for Vercel deployment with a production-ready structure.

## 📁 New Project Structure

```
SafeNet-AI/
├── api/                          # Vercel serverless functions
│   └── index.py                  # Entry point for Vercel
│
├── backend/                      # Main Flask application
│   ├── templates/                # ✨ MOVED from frontend/
│   │   ├── admin/
│   │   │   ├── dashboard.html
│   │   │   ├── messages.html
│   │   │   ├── sales.html
│   │   │   └── users.html
│   │   ├── partials/
│   │   │   └── footer.html
│   │   ├── 403.html
│   │   ├── contact.html
│   │   ├── dashboard.html
│   │   ├── disclaimer.html
│   │   ├── faq.html
│   │   ├── home.html
│   │   ├── login.html
│   │   ├── payment_cancel.html
│   │   ├── payment_success.html
│   │   ├── pricing.html
│   │   ├── privacy.html
│   │   ├── register.html
│   │   ├── scan.html
│   │   └── terms.html
│   │
│   ├── static/                   # ✨ MOVED from frontend/
│   │   ├── css/
│   │   │   ├── admin.css
│   │   │   ├── chatbot.css
│   │   │   ├── dashboard.css
│   │   │   ├── home.css
│   │   │   ├── legal.css
│   │   │   └── style.css
│   │   ├── images/
│   │   │   ├── brian_krebs.jpg
│   │   │   ├── dave_jevans.jpg
│   │   │   └── troy_hunt.jpg
│   │   ├── js/
│   │   │   ├── chatbot.js
│   │   │   ├── global-shortcuts.js
│   │   │   ├── home.js
│   │   │   ├── legal.js
│   │   │   ├── login.js
│   │   │   ├── register.js
│   │   │   └── script.js
│   │   ├── favicon.ico
│   │   ├── favicon.png
│   │   └── favicon.svg
│   │
│   ├── model/                    # ML models
│   │   ├── best_model.pkl
│   │   ├── scaler.pkl
│   │   ├── model_metadata.pkl
│   │   └── confusion_matrices.png
│   │
│   ├── dataset/                  # Training data
│   ├── notebooks/                # Jupyter notebooks
│   │
│   ├── app.py                    # ✅ UPDATED - Main Flask app
│   ├── auth.py                   # Authentication
│   ├── blacklist_checker.py      # Blacklist checking
│   ├── content_analyzer.py       # Content analysis
│   ├── credit_manager.py         # Credit management
│   ├── credit_system.py          # Credit system
│   ├── db.py                     # Database operations
│   ├── feature_extraction.py     # Feature extraction
│   ├── pricing_config.py         # Pricing configuration
│   ├── report_generator.py       # PDF reports
│   ├── stripe_config.py          # Stripe configuration
│   ├── stripe_webhooks.py        # Stripe webhooks
│   ├── tiered_detection.py       # Detection engine
│   ├── train_model.py            # Model training
│   ├── user_plan_helper.py       # User plan utilities
│   └── word_generator.py         # DOCX reports
│
├── frontend/                     # Now empty (only package.json)
│   └── package.json
│
├── .env                          # Environment variables
├── .gitignore                    # Git ignore
├── .vercelignore                 # ✨ NEW - Vercel ignore
├── requirements.txt              # Python dependencies
├── vercel.json                   # ✨ NEW - Vercel config
├── wsgi.py                       # ✨ NEW - WSGI entry point
└── README.md                     # Documentation
```

## 🔧 Changes Made

### 1. **Moved Frontend Assets into Backend**
   - ✅ `frontend/templates/` → `backend/templates/`
   - ✅ `frontend/static/` → `backend/static/`

### 2. **Updated Flask Configuration**
   **File:** `backend/app.py`
   
   ```python
   # Before:
   template_dir = os.path.join(os.path.dirname(base_dir), 'frontend', 'templates')
   static_dir = os.path.join(os.path.dirname(base_dir), 'frontend', 'static')
   
   # After:
   template_dir = os.path.join(base_dir, 'templates')
   static_dir = os.path.join(base_dir, 'static')
   ```

### 3. **Created Vercel Entry Point**
   **File:** `api/index.py` ✨ NEW
   
   ```python
   import sys
   import os
   
   # Add the backend directory to Python path
   backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
   if backend_path not in sys.path:
       sys.path.insert(0, backend_path)
   
   # Import the Flask app
   from app import app
   
   handler = app
   ```

### 4. **Created Vercel Configuration**
   **File:** `vercel.json` ✨ NEW
   
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "api/index.py",
         "use": "@vercel/python",
         "config": {
           "maxLambdaSize": "50mb"
         }
       },
       {
         "src": "backend/static/**",
         "use": "@vercel/static"
       }
     ],
     "routes": [
       {
         "src": "/static/(.*)",
         "dest": "/backend/static/$1"
       },
       {
         "src": "/(.*)",
         "dest": "/api/index.py"
       }
     ],
     "env": {
       "PYTHONUNBUFFERED": "1"
     },
     "functions": {
       "api/index.py": {
         "memory": 3008,
         "maxDuration": 30
       }
     }
   }
   ```

### 5. **Created WSGI Entry Point**
   **File:** `wsgi.py` ✨ NEW
   
   For compatibility with other WSGI servers.

### 6. **Created .vercelignore**
   **File:** `.vercelignore` ✨ NEW
   
   Excludes unnecessary files from deployment.

## 🚀 Deploying to Vercel

### Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI** (optional): `npm install -g vercel`
3. **Git Repository**: Your code should be in a Git repository

### Method 1: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub/GitLab/Bitbucket**
   ```bash
   git add .
   git commit -m "Reorganized for Vercel deployment"
   git push origin main
   ```

2. **Import Project in Vercel**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Click "Import Git Repository"
   - Select your repository
   - Vercel will auto-detect the configuration from `vercel.json`

3. **Configure Environment Variables**
   In Vercel Dashboard → Settings → Environment Variables, add:
   
   ```
   MONGO_URI=mongodb+srv://...
   GEMINI_API_KEY=your_key
   GOOGLE_CLIENT_ID=your_id
   GOOGLE_CLIENT_SECRET=your_secret
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_ID_BASIC=price_...
   STRIPE_PRICE_ID_PRO=price_...
   STRIPE_PRICE_ID_PRO_PLUS=price_...
   BASE_URL=https://your-app.vercel.app
   STRIPE_SUCCESS_URL=https://your-app.vercel.app/payment/success?session_id={CHECKOUT_SESSION_ID}
   STRIPE_CANCEL_URL=https://your-app.vercel.app/pricing?canceled=true
   ```

4. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy your app
   - You'll get a URL like: `https://your-app.vercel.app`

### Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Set Environment Variables**
   ```bash
   vercel env add MONGO_URI
   vercel env add GEMINI_API_KEY
   # ... add all environment variables
   ```

5. **Deploy to Production**
   ```bash
   vercel --prod
   ```

## ⚙️ Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb+srv://...` |
| `GEMINI_API_KEY` | Google Gemini AI API key | `AIzaSy...` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `798150...` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | `GOCSPX-...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `pk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | `whsec_...` |
| `STRIPE_PRICE_ID_BASIC` | Basic plan price ID | `price_...` |
| `STRIPE_PRICE_ID_PRO` | Pro plan price ID | `price_...` |
| `STRIPE_PRICE_ID_PRO_PLUS` | Pro Plus plan price ID | `price_...` |
| `BASE_URL` | Your app URL | `https://your-app.vercel.app` |
| `STRIPE_SUCCESS_URL` | Stripe success redirect | Include `{CHECKOUT_SESSION_ID}` |
| `STRIPE_CANCEL_URL` | Stripe cancel redirect | Full URL |

## 🧪 Testing Locally

### 1. Test with api/index.py (Vercel simulation)
```bash
python api/index.py
```
Visit: `http://127.0.0.1:5000`

### 2. Test with backend/app.py directly
```bash
cd backend
python app.py
```
Visit: `http://127.0.0.1:5000`

Both methods should work identically!

## ✅ Verification Checklist

Before deploying, verify:

- [ ] All templates render correctly
- [ ] All CSS files load properly
- [ ] All JavaScript files work
- [ ] All images display correctly
- [ ] Static files accessible at `/static/...`
- [ ] Routes work as expected
- [ ] Database connections configured
- [ ] Environment variables set
- [ ] ML model loads successfully
- [ ] Authentication works
- [ ] Stripe integration configured
- [ ] Admin dashboard accessible

## 🔍 Troubleshooting

### Issue: Static files not loading

**Solution:** Check `vercel.json` routes configuration. Ensure:
```json
{
  "src": "/static/(.*)",
  "dest": "/backend/static/$1"
}
```

### Issue: Import errors

**Solution:** Verify `api/index.py` path configuration:
```python
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)
```

### Issue: Templates not found

**Solution:** Check Flask configuration in `backend/app.py`:
```python
template_dir = os.path.join(base_dir, 'templates')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
```

### Issue: Serverless function timeout

**Solution:** Optimize code or increase timeout in `vercel.json`:
```json
"functions": {
  "api/index.py": {
    "maxDuration": 60
  }
}
```

### Issue: ML model too large

**Solution:** 
1. Use model compression
2. Load model from external storage (S3, GCS)
3. Increase lambda size in `vercel.json`

## 📝 Important Notes

1. **Serverless Limitations:**
   - Max execution time: 30 seconds (can extend to 60s on Pro)
   - Max deployment size: 50MB
   - Cold starts may occur

2. **ML Model:**
   - Ensure model files are in `backend/model/`
   - Model is loaded on first request (cold start)
   - Consider caching strategies

3. **Database:**
   - Use MongoDB Atlas (serverless-compatible)
   - Configure connection pooling
   - Handle connection timeouts

4. **Static Files:**
   - Served directly by Vercel CDN
   - Cached for better performance
   - Use `url_for('static', filename='...')` in templates

5. **Environment Variables:**
   - Never commit `.env` to Git
   - Set all variables in Vercel Dashboard
   - Update `BASE_URL` to your Vercel domain

## 🎉 Deployment Success!

Once deployed, your app will be available at:
```
https://your-app.vercel.app
```

### Features Preserved:
✅ AI phishing detection  
✅ ML model loading  
✅ User authentication  
✅ Google OAuth  
✅ Stripe payment integration  
✅ Admin dashboard  
✅ Report generation (PDF/DOCX)  
✅ Credit system  
✅ Database operations  
✅ All routes and functionality  

## 📚 Additional Resources

- [Vercel Python Documentation](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)

## 🆘 Need Help?

If you encounter issues:
1. Check Vercel deployment logs
2. Test locally first with `python api/index.py`
3. Verify all environment variables are set
4. Check Vercel function logs in dashboard

---

**Created**: 2024  
**Last Updated**: After project reorganization  
**Status**: ✅ Ready for deployment
