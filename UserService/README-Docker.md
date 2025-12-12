# UserService Docker Setup

This guide explains how to run the UserService using Docker and Docker Compose.

## Prerequisites

- Docker Desktop for Windows (or Docker Engine on Linux/Mac)
- Docker Compose (included with Docker Desktop)
- `.env` file configured with your environment variables

## Quick Start

### Development Environment (with MongoDB and RabbitMQ)

Start all services including MongoDB and RabbitMQ:

```powershell
docker-compose up -d
```

View logs:

```powershell
docker-compose logs -f userservice
```

Stop all services:

```powershell
docker-compose down
```

Stop and remove volumes:

```powershell
docker-compose down -v
```

### Production Environment (external MongoDB and RabbitMQ)

For production, use the production compose file that connects to existing external services:

```powershell
docker-compose -f docker-compose.prod.yml up -d
```

## Docker Commands

### Build the Image

```powershell
docker build -t user-service:latest .
```

### Run Container Only

If you want to run just the UserService container (assuming MongoDB and RabbitMQ are already running):

```powershell
docker run -d `
  --name user-service `
  -p 8001:8001 `
  --env-file .env `
  user-service:latest
```

### Check Container Status

```powershell
docker ps
```

### View Logs

```powershell
docker logs -f user-service
```

### Execute Commands in Container

```powershell
docker exec -it user-service bash
```

### Restart Container

```powershell
docker restart user-service
```

### Stop and Remove Container

```powershell
docker stop user-service
docker rm user-service
```

## Docker Compose Commands

### Start Services

```powershell
# Start in detached mode
docker-compose up -d

# Start with build
docker-compose up -d --build

# Start specific service
docker-compose up -d userservice
```

### Stop Services

```powershell
# Stop all services
docker-compose stop

# Stop specific service
docker-compose stop userservice
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f userservice

# Last 100 lines
docker-compose logs --tail=100 userservice
```

### Rebuild Services

```powershell
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build userservice

# Rebuild without cache
docker-compose build --no-cache
```

### Scale Services

```powershell
docker-compose up -d --scale userservice=3
```

## Environment Configuration

Ensure your `.env` file contains all required variables:

```env
PROJECT_NAME="user-management-service"
SERVER_PORT=8001
MONGO_CONNECTION_STRING="mongodb://username:password@host:port/database"
MONGO_DATABASE="testing_timesmartai"
JWT_SECRET="your-secret-key"
# ... other variables
```

## Accessing Services

- **UserService API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MongoDB**: localhost:27017

## Health Checks

The service includes health checks. Check health status:

```powershell
# Via API
curl http://localhost:8001/health

# Via Docker
docker inspect --format='{{.State.Health.Status}}' user-service
```

## Troubleshooting

### Container won't start

Check logs:
```powershell
docker-compose logs userservice
```

### Database connection issues

Ensure MongoDB is running and accessible:
```powershell
docker-compose ps mongodb
docker-compose logs mongodb
```

### Port already in use

Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8002:8001"  # Map to different host port
```

### Rebuild after code changes

```powershell
docker-compose up -d --build userservice
```

### Clean up everything

```powershell
# Remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker rmi user-service:latest
```

## Production Deployment

For production deployment:

1. Use `docker-compose.prod.yml` which excludes local MongoDB/RabbitMQ
2. Set appropriate resource limits
3. Use production environment variables
4. Enable log rotation
5. Use Docker secrets for sensitive data

```powershell
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring

Monitor container resources:

```powershell
# Real-time stats
docker stats user-service

# Via docker-compose
docker-compose stats
```

## Backup and Restore

### MongoDB Backup

```powershell
docker exec mongodb mongodump --out /backup --username=<user> --password=<pass>
docker cp mongodb:/backup ./backup
```

### MongoDB Restore

```powershell
docker cp ./backup mongodb:/backup
docker exec mongodb mongorestore /backup --username=<user> --password=<pass>
```

## Network

Services communicate via the `timesmart-network` bridge network. To connect other services:

```yaml
networks:
  - timesmart-network

networks:
  timesmart-network:
    external: true
```
