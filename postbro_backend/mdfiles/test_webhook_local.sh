#!/bin/bash

# Quick script to test webhooks locally
# Usage: ./test_webhook_local.sh

echo "🚀 PostBro Webhook Local Testing Setup"
echo "========================================"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    echo "Install with:"
    echo "  brew install ngrok"
    echo ""
    echo "Or download from: https://ngrok.com/download"
    exit 1
fi

echo "✅ ngrok found"
echo ""

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo "⚠️  Docker doesn't seem to be running"
    echo "   Make sure Docker is started"
    echo ""
fi

echo "📋 Setup Steps:"
echo ""
echo "1. Start Django backend:"
echo "   docker compose up backend"
echo ""
echo "2. In another terminal, start ngrok:"
echo "   ngrok http 8000"
echo ""
echo "3. Copy the HTTPS URL from ngrok (e.g., https://abc123.ngrok.io)"
echo ""
echo "4. Configure in Dodo Payments dashboard:"
echo "   Webhook URL: https://YOUR-NGROK-URL/api/billing/webhook/dodo/"
echo ""
echo "5. View requests in ngrok dashboard:"
echo "   http://localhost:4040"
echo ""
echo "6. Watch Django logs:"
echo "   docker compose logs -f backend"
echo ""
echo "🧪 Test webhook handlers directly:"
echo "   docker compose exec backend python manage.py test_webhook payment.succeeded --subscription-id=UUID --user-id=UUID"
echo ""
echo "📚 Full guide: See WEBHOOK_LOCAL_TESTING.md"
echo ""

