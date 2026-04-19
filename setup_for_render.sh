#!/bin/bash

# Script to prepare and test Django project before deploying to Render

echo "========================================="
echo "Django Project Setup for Render"
echo "========================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python --version
echo ""

# Install requirements
echo "✓ Installing dependencies..."
pip install -r requirements.txt
echo ""

# Create environment file
echo "✓ Checking .env file..."
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠ Please edit .env file with your settings"
else
    echo ".env file already exists"
fi
echo ""

# Run collectstatic (simulating Render build process)
echo "✓ Collecting static files (this is done automatically on Render)..."
python manage.py collectstatic --noinput
echo ""

# Run migrations
echo "✓ Running migrations..."
python manage.py migrate
echo ""

echo "========================================="
echo "✅ Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Run 'python manage.py runserver' to test locally"
echo "2. Test all functionality locally"
echo "3. Commit changes: git add . && git commit -m 'Configure for Render deployment'"
echo "4. Push to GitHub: git push origin main"
echo "5. Deploy on Render using instructions in RENDER_DEPLOYMENT.md"
echo ""
