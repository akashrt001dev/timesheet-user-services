#!/bin/bash

# Development Startup Script for User Management Service
# Simple, lightweight script for development environment

set -e

# Configuration - Matches your .env file
PROJECT_DIR="$(pwd)"  # Uses current directory, or set your path
VENV_NAME="venv"
APP_MODULE="app.main:app"
HOST="0.0.0.0"  # Matches your .env HOST
PORT="8001"     # Matches your .env PORT
LOG_LEVEL="info" # Matches your .env LOG_LEVEL

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# PID file for tracking the process
PID_FILE="$PROJECT_DIR/.dev-server.pid"

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if server is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Activate virtual environment
activate_venv() {
    if [ -f "$PROJECT_DIR/$VENV_NAME/bin/activate" ]; then
        log "Activating virtual environment..."
        source "$PROJECT_DIR/$VENV_NAME/bin/activate"
        success "Virtual environment activated"
    else
        warning "Virtual environment not found at $PROJECT_DIR/$VENV_NAME"
        warning "Creating virtual environment..."
        python3 -m venv "$PROJECT_DIR/$VENV_NAME"
        source "$PROJECT_DIR/$VENV_NAME/bin/activate"
        
        if [ -f "requirements.txt" ]; then
            log "Installing dependencies..."
            pip install --upgrade pip setuptools
            pip install -r requirements.txt
        fi
        
        # Install uvicorn if not present
        pip install uvicorn[standard] python-dotenv
        success "Virtual environment created and dependencies installed"
    fi
}

# Install or update dependencies
install_deps() {
    log "Installing/updating dependencies..."
    activate_venv
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip setuptools
        pip install -r requirements.txt
        success "Dependencies updated"
    else
        warning "No requirements.txt found"
    fi
    
    # Ensure uvicorn is installed
    pip install uvicorn[standard] python-dotenv
}

# Start the development server
start_server() {
    log "Starting development server..."
    
    if is_running; then
        warning "Server is already running (PID: $(cat $PID_FILE))"
        show_info
        return 0
    fi
    
    cd "$PROJECT_DIR"
    activate_venv
    mkdir -p logs
    
    if [ ! -f "app/main.py" ]; then
        error "main.py not found in $PROJECT_DIR"
        error "Make sure you're in the correct project directory"
        exit 1
    fi
    
    log "Starting FastAPI server with auto-reload..."
    nohup uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --log-level "$LOG_LEVEL" \
        --reload \
        --access-log \
        > logs/dev-server.log 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    sleep 3
    if is_running; then
        success "Development server started successfully!"
        show_info
    else
        error "Failed to start server. Check logs:"
        tail -20 logs/dev-server.log
        exit 1
    fi
}

# Stop the development server
stop_server() {
    log "Stopping development server..."
    if ! is_running; then
        warning "Server is not running"
        return 0
    fi
    local pid=$(cat "$PID_FILE")
    log "Stopping server (PID: $pid)..."
    kill -TERM "$pid" 2>/dev/null || true
    local count=0
    while [ $count -lt 10 ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
    done
    if ps -p "$pid" > /dev/null 2>&1; then
        warning "Graceful shutdown failed, force killing..."
        kill -KILL "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    success "Development server stopped"
}

# Restart the server
restart_server() {
    log "Restarting development server..."
    stop_server
    sleep 2
    start_server
}

# Show server status and info
status_server() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        success "Development server is running (PID: $pid)"
        show_info
        if [ -f "logs/dev-server.log" ]; then
            echo -e "\n${BLUE}Recent logs (last 10 lines):${NC}"
            tail -10 logs/dev-server.log
        fi
    else
        warning "Development server is not running"
    fi
}

# Show server information
show_info() {
    echo -e "\n${GREEN}🚀 Development Server Info:${NC}"
    echo -e "   📍 URL: ${BLUE}http://$HOST:$PORT${NC}"
    echo -e "   📚 API Docs: ${BLUE}http://$HOST:$PORT/docs${NC}"
    echo -e "   🔍 Health: ${BLUE}http://$HOST:$PORT/health${NC}"
    echo -e "   📊 Logs: ${BLUE}tail -f logs/dev-server.log${NC}"
    echo -e "   🔄 Auto-reload: ${GREEN}ENABLED${NC}"
    echo -e "   🔄 Manual restart: ${BLUE}./startup.sh restart${NC}"
    echo ""
}

# Show development logs
show_logs() {
    if [ -f "logs/dev-server.log" ]; then
        case "${2:-tail}" in
            "follow"|"f")
                echo -e "${BLUE}Following development logs (Ctrl+C to exit):${NC}"
                tail -f logs/dev-server.log
                ;;
            "all")
                cat logs/dev-server.log
                ;;
            "clear")
                > logs/dev-server.log
                success "Logs cleared"
                ;;
            *)
                tail -30 logs/dev-server.log
                ;;
        esac
    else
        warning "No logs found. Server may not have been started yet."
    fi
}

# Quick health check
health_check() {
    if ! is_running; then
        error "Server is not running"
        return 1
    fi
    log "Checking server health..."
    if command -v curl &> /dev/null; then
        if curl -f -s "http://$HOST:$PORT/health" > /dev/null; then
            success "✅ Health check passed"
            echo -e "\n${BLUE}Health Response:${NC}"
            curl -s "http://$HOST:$PORT/health" | python3 -m json.tool 2>/dev/null || echo "Health endpoint responded"
        else
            error "❌ Health check failed"
            return 1
        fi
    else
        warning "curl not available, cannot test HTTP endpoint"
        success "Server process is running"
    fi
}

# Setup development environment
setup_dev() {
    log "Setting up development environment..."
    mkdir -p logs data config storage storage/temp uploads
    install_deps
    if [ ! -f ".env" ]; then
        log "Creating development .env file..."
        cat > .env << EOF
# User Management Service - Local Development Environment
# ======================================================

# Application Configuration
ENVIRONMENT=development
PORT=8001
DEBUG=true
LOG_LEVEL=INFO

# Database Configuration - QA MongoDB for Local Development
MONGODB_URL=mongodb://timesmartui:timesmartui@ec2-23-20-18-226.compute-1.amazonaws.com/qa_timesmartai
MONGODB_DATABASE=qa_timesmartai
MONGODB_HOST=ec2-23-20-18-226.compute-1.amazonaws.com
MONGODB_PORT=27017
MONGODB_USERNAME=timesmartui
MONGODB_PASSWORD=timesmartui

# Message Queue Configuration - Local RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=admin
RABBITMQ_PASSWORD=admin123
RABBITMQ_VHOST=/
MESSAGING_ENABLED=true

# Cache Configuration - Local Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT Configuration
JWT_SECRET=BvPHGM8C0ia4uOuxxqPD5DTbWC9F9TWvPStp3pb7ARo0oK2mJ3pd3YG4lxA9i8bj6OTbadwezxgeEByY
JWT_EXPIRATION=86400
JWT_ALGORITHM=HS256

# Server Configuration
SERVER_URL=http://localhost:8001/user-management-service
BASE_URL=http://localhost:8001
HOST=0.0.0.0

# Service Discovery (Eureka) - Enabled for development
EUREKA_ENABLED=true
EUREKA_SERVER_URL=http://localhost:8761/eureka
SERVICE_NAME=user-management-service
SERVER_HOST=localhost
SERVER_PORT=8001

# External Services
CONTRACT_SERVICE_URL=http://localhost:8002/
ENTITY_CLIENT_URL="http://localhost:8003/"
ENTITY_SERVICE_URL="http://localhost:8003/"
TIMESHEET_SERVICE_URL=http://localhost:8004/


# File Storage Configuration
FILE_STORAGE_PATH=./storage
TEMP_STORAGE_PATH=./storage/temp

# Scheduler Configuration
SCHEDULER_ENABLED=true
SCHEDULER_WORKER_COUNT=1

# File Upload Limits
MAX_FILE_SIZE=20971520
MAX_REQUEST_SIZE=26214400
EOF
        success ".env file created with development defaults"
    fi
    success "Development environment setup complete!"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "  1. Update .env file with your configuration"
    echo -e "  2. Run: ${BLUE}./startup.sh start${NC}"
    echo -e "  3. Open: ${BLUE}http://$HOST:$PORT/docs${NC}"
}

# Open browser (if possible)
open_browser() {
    local url="http://$HOST:$PORT"
    if ! is_running; then
        error "Server is not running. Start it first with: $0 start"
        return 1
    fi
    log "Opening browser..."
    if command -v xdg-open &> /dev/null; then
        xdg-open "$url"
    elif command -v open &> /dev/null; then
        open "$url"
    elif command -v start &> /dev/null; then
        start "$url"
    else
        success "Please open your browser and go to: $url"
    fi
}

# Main command handler
case "${1:-help}" in
    "start"|"run")
        start_server
        ;;
    "stop")
        stop_server
        ;;
    "restart")
        restart_server
        ;;
    "status")
        status_server
        ;;
    "logs")
        show_logs "$@"
        ;;
    "health")
        health_check
        ;;
    "setup")
        setup_dev
        ;;
    "deps"|"install")
        install_deps
        ;;
    "open"|"browser")
        open_browser
        ;;
    "info")
        show_info
        ;;
    "help"|*)
        echo -e "${GREEN}Development Startup Script for User Management Service${NC}"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo -e "${BLUE}Main Commands:${NC}"
        echo "  start       - Start development server with auto-reload"
        echo "  stop        - Stop development server"
        echo "  restart     - Restart development server"
        echo "  status      - Show server status and info"
        echo ""
        echo -e "${BLUE}Utility Commands:${NC}"
        echo "  setup       - Setup development environment"
        echo "  deps        - Install/update dependencies"
        echo "  health      - Check server health"
        echo "  logs        - Show logs (options: follow, all, clear)"
        echo "  open        - Open browser to application"
        echo "  info        - Show server information"
        echo ""
        echo -e "${BLUE}Examples:${NC}"
        echo "  $0 setup          # First time setup"
        echo "  $0 start          # Start development server"
        echo "  $0 restart        # Restart after code changes"
        echo "  $0 logs follow    # Watch logs in real-time"
        echo "  $0 open           # Open browser"
        echo ""
        echo -e "${YELLOW}Development Workflow:${NC}"
        echo "  1. $0 start       # Start server"
        echo "  2. Edit code      # Make your changes"
        echo "  3. $0 restart     # Apply changes"
        echo "  4. Test at http://$HOST:$PORT/docs"
        ;;
esac
