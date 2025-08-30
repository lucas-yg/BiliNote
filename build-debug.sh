#!/bin/bash

# Docker Build Debug and Optimization Script
set -e

echo "🔍 Docker Build Diagnostics"
echo "=========================="

echo "📊 Current Resource Usage:"
echo "Colima Status:"
colima status

echo "Docker Resources:"
docker system df

echo "Available Memory:"
vm_stat | head -3

echo "🧹 Cleaning Build Environment..."
docker system prune -f
docker builder prune -f

echo "🚀 Starting Optimized Build..."
echo "Building with reduced parallelism and memory limits..."

# Build with specific memory constraints
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Sequential build to avoid memory pressure
echo "Building backend first..."
docker-compose -f docker-compose.china.yml build backend

echo "Building frontend..."
docker-compose -f docker-compose.china.yml build frontend

echo "Building nginx..."
docker-compose -f docker-compose.china.yml build nginx

echo "✅ Build completed successfully!"
echo "📊 Final Resource Usage:"
docker system df