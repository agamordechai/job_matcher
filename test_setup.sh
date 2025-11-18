#!/bin/bash

# Test script to verify Job Matcher setup
# Run this after following the README instructions

echo "=========================================="
echo "Job Matcher Setup Test"
echo "=========================================="
echo ""

# Test 1: Check if Docker is running
echo "Test 1: Checking Docker..."
if docker info > /dev/null 2>&1; then
    echo "✓ Docker is running"
else
    echo "✗ Docker is not running - please start Docker Desktop"
    exit 1
fi
echo ""

# Test 2: Check if docker-compose file exists
echo "Test 2: Checking docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    echo "✓ docker-compose.yml found"
else
    echo "✗ docker-compose.yml not found"
    exit 1
fi
echo ""

# Test 3: Check if .env file exists
echo "Test 3: Checking .env file..."
if [ -f ".env" ]; then
    echo "✓ .env file found"
else
    echo "⚠ .env file not found - creating from .env.example"
    cp .env.example .env
    echo "  Please edit .env and add your API keys"
fi
echo ""

# Test 4: Start services
echo "Test 4: Starting Docker services..."
docker-compose up -d
sleep 10
echo ""

# Test 5: Check service status
echo "Test 5: Checking service status..."
docker-compose ps
echo ""

# Test 6: Test health endpoint
echo "Test 6: Testing health endpoint..."
sleep 5
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✓ Health endpoint is responding"
    curl -s http://localhost:8000/api/health | python3 -m json.tool
else
    echo "⚠ Health endpoint not responding yet"
    echo "  Try: curl http://localhost:8000/api/health"
    echo ""
    echo "  Checking app logs:"
    docker-compose logs --tail=20 app
fi
echo ""

# Test 7: Check if docs are accessible
echo "Test 7: Checking API documentation..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs | grep -q "200"; then
    echo "✓ API docs are accessible at http://localhost:8000/docs"
else
    echo "⚠ API docs not accessible yet"
fi
echo ""

echo "=========================================="
echo "Setup test complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Visit http://localhost:8000/docs for interactive API documentation"
echo "2. Upload a CV: POST /api/cv/upload"
echo "3. Create search filters: POST /api/filters/"
echo "4. View logs: docker-compose logs -f"
echo ""

