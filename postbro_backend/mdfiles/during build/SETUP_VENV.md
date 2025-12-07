# 🐍 Virtual Environment Setup Guide

## Quick Setup

```bash
# 1. Navigate to project
cd postbro_backend

# 2. Remove old venv (if exists)
rm -rf venv

# 3. Create new virtual environment
python3 -m venv venv

# 4. Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# 5. Upgrade pip
pip install --upgrade pip

# 6. Install all requirements
pip install -r requirements.txt

# 7. Verify installation
pip list
```

## Verify Setup

```bash
# Check Django is installed
python manage.py --version

# Check all packages
pip list | grep -i django
pip list | grep -i supabase
```

## Common Issues

**Issue: "python3: command not found"**
- Use `python` instead of `python3`
- Or install Python 3: `brew install python3` (macOS)

**Issue: "pip: command not found"**
- Make sure venv is activated
- Try: `python -m pip install -r requirements.txt`

**Issue: "Permission denied"**
- Make sure you have write permissions
- Try: `sudo python3 -m venv venv` (not recommended, better to fix permissions)

