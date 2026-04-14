#!/bin/bash

# Set UTF-8 encoding (Mac/Linux)
export LANG=en_US.UTF-8

echo "========================================"
echo "   TestHub Document Parser Startup (Linux/Mac)"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Check configuration file
# Note: Script is in backend directory, need to read config.yaml from parent directory
if [ ! -f "../config.yaml" ]; then
    echo "Error: Configuration file ../config.yaml not found"
    exit 1
fi

# Read document parser URL from config.yaml
# Format: doc_parser_url: "http://localhost:9987"
DOC_PARSER_URL=$(grep -E "^\s*doc_parser_url:" ../config.yaml | sed 's/.*doc_parser_url:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr -d ' ')

# Read Tika timeout from config.yaml
TIKA_TIMEOUT=$(grep -E "^\s*tika_timeout:" ../config.yaml | sed 's/.*tika_timeout:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr -d ' ')

# Read Tika memory from config.yaml
TIKA_MEMORY=$(grep -E "^\s*tika_memory:" ../config.yaml | sed 's/.*tika_memory:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr -d ' ')

# Use default values if not found
if [ -z "$DOC_PARSER_URL" ]; then
    DOC_PARSER_URL="http://localhost:9987"
fi
if [ -z "$TIKA_TIMEOUT" ]; then
    TIKA_TIMEOUT=180
fi
if [ -z "$TIKA_MEMORY" ]; then
    TIKA_MEMORY="2g"
fi

# Parse URL to get host and port
# URL format: http://localhost:9987 or https://localhost:9987
# Remove protocol prefix
URL_NO_PROTO="${DOC_PARSER_URL#*://}"

# Extract host and port
# Format: localhost:9987 or localhost
TIKA_HOST=$(echo "$URL_NO_PROTO" | cut -d':' -f1 | cut -d'/' -f1)
TIKA_PORT=$(echo "$URL_NO_PROTO" | cut -d':' -f2 | cut -d'/' -f1)

# Use default values if parsing failed
if [ -z "$TIKA_HOST" ]; then
    TIKA_HOST="localhost"
fi
if [ -z "$TIKA_PORT" ]; then
    TIKA_PORT="9987"
fi

echo "Configuration:"
echo "  - URL: $DOC_PARSER_URL"
echo "  - Host: $TIKA_HOST"
echo "  - Port: $TIKA_PORT"
echo "  - Timeout: ${TIKA_TIMEOUT}s"
echo "  - Memory: $TIKA_MEMORY"
echo ""

# Check Java environment
echo "Checking Java environment..."
if ! command -v java &> /dev/null; then
    echo "Error: Java not found! Please install Java runtime environment."
    exit 1
fi
echo "Java environment OK"
echo ""

# Check if tika-server.jar exists
TIKA_JAR="../expand/doc_analysis/tika-server.jar"
if [ ! -f "$TIKA_JAR" ]; then
    echo "Error: tika-server.jar not found!"
    echo "Expected path: $TIKA_JAR"
    exit 1
fi

echo "Starting Tika Server..."
echo "Press Ctrl+C to stop the server"
echo ""

# Function to handle cleanup
cleanup() {
    echo ""
    echo "Stopping Tika Server..."
    if [ -n "$TIKA_PID" ]; then
        kill $TIKA_PID 2>/dev/null
    fi
    rm -f tika_server.pid
    echo "Tika Server stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Tika Server
java -Djava.awt.headless=true -Xmx$TIKA_MEMORY -jar "$TIKA_JAR" --host="$TIKA_HOST" --port="$TIKA_PORT" &
TIKA_PID=$!

# Wait a moment to check if process started successfully
sleep 2

# Check if process is running
if kill -0 $TIKA_PID 2>/dev/null; then
    echo "Tika Server started (PID: $TIKA_PID)"
    echo ""
    echo "========================================"
    echo "   Document Parser Service Running"
    echo "========================================"
    echo ""
    echo "Process information:"
    echo "  - Tika Server: PID $TIKA_PID"
    echo ""
    echo "Tips:"
    echo "  - Stop service: kill $TIKA_PID"
    echo "  - Or press Ctrl+C to stop"
    echo ""
    
    # Save PID to file
    echo "$TIKA_PID" > tika_server.pid
    
    # Keep script running
    wait $TIKA_PID
else
    echo "Tika Server startup failed"
    exit 1
fi
