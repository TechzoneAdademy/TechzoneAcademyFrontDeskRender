# Troubleshooting Guide for TechZone Portal on Render

## Common Build Errors and Solutions

### 1. Pandas Compilation Error (Python 3.13 Compatibility)

**Error:** `error: too few arguments to function '_PyLong_AsByteArray'`

**Cause:** Pandas 2.1.4 is not compatible with Python 3.13 due to API changes.

**Solution:** 
- Use Python 3.11.9 (specified in `runtime.txt`)
- Use pandas 2.0.3 (more stable, better compatibility)
- Ensure `PYTHON_VERSION` environment variable is set to `3.11.9` in Render

**Files to check:**
- ✅ `runtime.txt` should contain `python-3.11.9`
- ✅ `requirements.txt` should have `pandas==2.0.3`
- ✅ `render.yaml` should specify `PYTHON_VERSION: 3.11.9`

### 2. Build Command Issues

**Problem:** Build fails during dependency installation

**Solutions:**
1. **Clear Render cache:**
   - Go to your service dashboard
   - Click "Manual Deploy" → "Clear Build Cache & Deploy"

2. **Check requirements.txt format:**
   - Ensure no extra spaces or special characters
   - Use exact version numbers (e.g., `Flask==2.3.3`)

3. **Verify Python version compatibility:**
   - All packages must support Python 3.11
   - Check package compatibility on PyPI

### 3. Import Errors

**Problem:** `ModuleNotFoundError` or import failures

**Common causes:**
- Missing dependencies in `requirements.txt`
- Incorrect import paths
- Case sensitivity issues

**Solutions:**
1. **Check all imports in your code:**
   ```python
   # Ensure these are in requirements.txt
   from flask import Flask
   import pandas as pd
   from firebase_admin import credentials
   ```

2. **Verify file structure:**
   ```
   ├── app.py
   ├── portalflask/
   │   ├── __init__.py  # Make sure this exists
   │   ├── AI_firebase.py
   │   └── ...
   ```

### 4. Environment Variable Issues

**Problem:** App fails to start due to missing configuration

**Required variables:**
- `FIREBASE_CONFIG` - Firebase service account JSON
- `EMAIL_ADDRESS` - Gmail address
- `EMAIL_PASSWORD` - Gmail App Password

**How to set in Render:**
1. Go to your service dashboard
2. Click "Environment" tab
3. Add each variable with `sync: false` for sensitive data

### 5. Port Binding Issues

**Problem:** `Address already in use` or port binding errors

**Solution:** Ensure start command is correct:
```bash
gunicorn app:techzone_app --bind 0.0.0.0:$PORT
```

**Note:** `$PORT` is automatically set by Render, don't change it.

## Quick Fix Checklist

Before redeploying, verify:

- [ ] `runtime.txt` contains `python-3.11.9`
- [ ] `requirements.txt` has compatible package versions
- [ ] `render.yaml` specifies correct Python version
- [ ] All environment variables are set in Render dashboard
- [ ] Start command uses `gunicorn app:techzone_app --bind 0.0.0.0:$PORT`

## Package Version Compatibility Matrix

| Package | Python 3.11 | Python 3.12 | Python 3.13 |
|---------|-------------|-------------|-------------|
| Flask 2.3.3 | ✅ | ✅ | ❌ |
| pandas 2.0.3 | ✅ | ✅ | ❌ |
| firebase-admin 6.2.0 | ✅ | ✅ | ✅ |
| gunicorn 21.2.0 | ✅ | ✅ | ✅ |

## Recommended Python Version: 3.11.9

**Why Python 3.11.9?**
- Stable and mature
- Excellent package compatibility
- Good performance
- Widely supported by all major packages

## If Problems Persist

1. **Check Render logs** for specific error messages
2. **Verify GitHub repository** has all latest changes
3. **Clear build cache** and redeploy
4. **Check package compatibility** on PyPI
5. **Consider downgrading** problematic packages

## Support Resources

- [Render Documentation](https://render.com/docs)
- [Python Package Index](https://pypi.org)
- [Flask Documentation](https://flask.palletsprojects.com)
- [Pandas Documentation](https://pandas.pydata.org)
