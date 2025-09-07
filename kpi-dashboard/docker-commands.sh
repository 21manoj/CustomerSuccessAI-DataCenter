#!/bin/bash
# Docker management commands for KPI Dashboard

case "$1" in
    "build")
        echo "🐳 Building Docker containers..."
        docker-compose build
        ;;
    "start")
        echo "🚀 Starting services..."
        docker-compose up -d
        ;;
    "stop")
        echo "🛑 Stopping services..."
        docker-compose down
        ;;
    "restart")
        echo "🔄 Restarting services..."
        docker-compose restart
        ;;
    "logs")
        echo "📋 Showing logs..."
        docker-compose logs -f
        ;;
    "status")
        echo "📊 Service status:"
        docker-compose ps
        ;;
    "clean")
        echo "🧹 Cleaning up..."
        docker-compose down -v
        docker system prune -f
        ;;
    "shell-backend")
        echo "🐚 Opening backend shell..."
        docker-compose exec backend /bin/bash
        ;;
    "shell-frontend")
        echo "🐚 Opening frontend shell..."
        docker-compose exec frontend /bin/sh
        ;;
    "test")
        echo "🧪 Testing services..."
        echo "Backend: http://localhost:5059"
        curl -f http://localhost:5059/ && echo "✅ Backend OK" || echo "❌ Backend Failed"
        echo "Frontend: http://localhost:3000"
        curl -f http://localhost:3000/ && echo "✅ Frontend OK" || echo "❌ Frontend Failed"
        ;;
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|status|clean|shell-backend|shell-frontend|test}"
        echo ""
        echo "Commands:"
        echo "  build          - Build Docker containers"
        echo "  start          - Start services"
        echo "  stop           - Stop services"
        echo "  restart        - Restart services"
        echo "  logs           - Show logs"
        echo "  status         - Show service status"
        echo "  clean          - Clean up containers and volumes"
        echo "  shell-backend  - Open backend container shell"
        echo "  shell-frontend - Open frontend container shell"
        echo "  test           - Test service health"
        exit 1
        ;;
esac
