# FULFILLMENT APP - MAKEFILE
# Convenient commands for Docker deployment

.PHONY: help build up down restart logs status clean

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║          FULFILLMENT APP - DOCKER COMMANDS                 ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-logs     - View development logs"
	@echo "  make dev-down     - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-logs    - View production logs"
	@echo "  make prod-down    - Stop production environment"
	@echo "  make deploy       - Build and deploy to production"
	@echo ""
	@echo "Database:"
	@echo "  make db-backup    - Backup database"
	@echo "  make db-shell     - Open database shell"
	@echo "  make db-migrate   - Run migrations"
	@echo ""
	@echo "Utilities:"
	@echo "  make status       - Check container status"
	@echo "  make logs         - View all logs"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make rebuild      - Rebuild all images"
	@echo ""

# Development commands
dev:
	docker-compose up -d
	@echo "✅ Development environment started"
	@echo "   Backend:  http://localhost:3001"
	@echo "   Frontend: http://localhost:3002"
	@echo "   DB:       localhost:5433"

dev-logs:
	docker-compose logs -f

dev-down:
	docker-compose down

# Production commands
prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production environment started"

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-down:
	docker-compose -f docker-compose.prod.yml down

deploy:
	@echo "🚀 Deploying to production..."
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Deployment complete!"

# Database commands
db-backup:
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S) && \
	docker exec fulfillment-db-prod pg_dump -U fulfillment_user fulfillment > backups/fulfillment_$$DATE.sql && \
	gzip backups/fulfillment_$$DATE.sql && \
	echo "✅ Backup created: backups/fulfillment_$$DATE.sql.gz"

db-shell:
	docker exec -it fulfillment-db-prod psql -U fulfillment_user -d fulfillment

db-migrate:
	docker exec -i fulfillment-db-prod psql -U fulfillment_user -d fulfillment < backend/migrations/001_initial_schema.sql
	@echo "✅ Migrations complete"

# Utility commands
status:
	@echo "📦 Container Status:"
	@docker ps --filter "name=fulfillment" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "💾 Volume Status:"
	@docker volume ls --filter "name=fulfillment"
	@echo ""
	@echo "🌐 Health Checks:"
	@curl -s http://localhost:3001/health 2>/dev/null | jq || echo "Backend not responding"

logs:
	docker-compose -f docker-compose.prod.yml logs -f --tail=100

restart:
	docker-compose -f docker-compose.prod.yml restart

rebuild:
	docker-compose -f docker-compose.prod.yml build --no-cache
	docker-compose -f docker-compose.prod.yml up -d

clean:
	@echo "⚠️  This will remove all containers and volumes!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose -f docker-compose.prod.yml down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

# Quick commands
build:
	docker-compose -f docker-compose.prod.yml build

up:
	docker-compose -f docker-compose.prod.yml up -d

down:
	docker-compose -f docker-compose.prod.yml down

