.PHONY: help setup install clean run-client run-server start-server stop-server restart-server dev-server build-server docker-up docker-down docker-detached docker-logs docker-stop docker-restart docker-build init-keys

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@sed -n 's/^\([a-zA-Z_-]*\):.*##\(.*\)/  \1\t\2/p' $(MAKEFILE_LIST) | column -t -s '	'

setup: ## Setup virtual environment and install dependencies
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
		echo "Virtual environment created"; \
	else \
		echo "Virtual environment already exists"; \
	fi
	@echo "Upgrading pip..."
	@.venv/bin/pip install --upgrade pip -q
	@echo "Installing dependencies..."
	@if [ -f "requirements.txt" ]; then \
		.venv/bin/pip install -r requirements.txt; \
	else \
		echo "Warning: requirements.txt not found"; \
	fi
	@echo "Setup complete!"

install: setup ## Alias for setup

clean: ## Remove virtual environment
	@echo "Removing virtual environment..."
	@rm -rf .venv
	@echo "Clean complete"

run-client: ## Run the WebSocket client
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Running setup first..."; \
		$(MAKE) setup; \
	fi
	@echo "Starting client..."
	@.venv/bin/python client.py

run-server: ## Run the FastAPI server (requires setup)
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Running setup first..."; \
		$(MAKE) setup; \
	fi
	@echo "Starting server..."
	@.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-server: ## Run the server in development mode with hot reload
	$(MAKE) run-server

init-keys: ## Initialize Docker volumes with server keys
	@bash init_keys.sh

start-server: ## Start the server in background
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Running setup first..."; \
		$(MAKE) setup; \
	fi
	@if [ -f ".server.pid" ]; then \
		if ps -p $(cat .server.pid) > /dev/null 2>&1; then \
			echo "Server is already running (PID: $(cat .server.pid))"; \
			exit 1; \
		else \
			rm -f .server.pid; \
		fi; \
	fi
	@echo "Starting server in background..."
	@nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 & echo $$! > .server.pid
	@echo "Server started (PID: $(cat .server.pid))"
	@echo "Logs: server.log"
	@echo "To stop: make stop-server"

stop-server: ## Stop the background server
	@if [ ! -f ".server.pid" ]; then \
		echo "Server is not running or was stopped manually"; \
		exit 1; \
	fi
	@pid=$$(cat .server.pid); \
	if ps -p $$pid > /dev/null 2>&1; then \
		echo "Stopping server (PID: $$pid)..."; \
		kill $$pid; \
		rm -f .server.pid; \
		echo "Server stopped"; \
	else \
		echo "Server process (PID: $$pid) not found, cleaning up"; \
		rm -f .server.pid; \
	fi

restart-server: stop-server start-server ## Restart the background server

build-server: ## Build the Docker image
	@echo "Building Docker image..."
	@docker build -t locopycat .

docker-run: build-server ## Run the server in Docker
	@echo "Running server in Docker..."
	@docker run -p 8000:8000 locopycat

docker-up: ## Start services with docker-compose (foreground)
	@echo "Starting services with docker-compose..."
	@docker-compose up

docker-detached: ## Start services with docker-compose in background
	@echo "Starting services in detached mode..."
	@docker-compose up -d
	@echo "Services started in background"
	@echo "To view logs: make docker-logs"
	@echo "To stop: make docker-down"

docker-down: ## Stop services with docker-compose
	@echo "Stopping services with docker-compose..."
	@docker-compose down

docker-stop: docker-down ## Alias for docker-down

docker-logs: ## View container logs
	@docker-compose logs -f

docker-restart: ## Restart services
	@echo "Restarting services..."
	@docker-compose restart

docker-build: ## Rebuild and start services with docker-compose
	@echo "Rebuilding and starting services..."
	@docker-compose up --build
