# Eureka Service Discovery Setup Guide

## Current Status

The Eureka service discovery is **optional** and disabled by default. The application will start and function normally without it.

### Why Eureka Registration Was Failing

1. **No Eureka Server Running**: The default config pointed to `http://localhost:8761/eureka`, but no Eureka server was available
2. **Docker Networking Issue**: When running in Docker, `localhost` is not reachable from other containers. The service tried to register with an invalid hostname
3. **Configuration Mismatch**: `SERVER_PORT` was set to 8000 but Docker exposed port 8001

## Quick Fix Applied

The following changes were made to resolve the errors:

### 1. **config.py Changes**
- `EUREKA_SERVER_URL` is now empty by default (Eureka is disabled)
- `SERVER_HOST` changed from `localhost` to `user-service` (Docker container hostname)
- `SERVER_PORT` changed from 8000 to 8001 (matches docker-compose exposure)

### 2. **eureka_client.py Changes**
- Added `enabled` flag that checks if `EUREKA_SERVER_URL` is configured
- If disabled, registration/heartbeat/deregistration operations return success without attempting connection
- Improved error logging to indicate Eureka server unavailability
- All methods now gracefully skip if Eureka is not enabled

## Result

✅ Service starts without Eureka errors
✅ "Eureka registration failed; service will continue without discovery" warning is expected when Eureka is disabled
✅ No impact on core application functionality

---

## Optional: Enable Eureka Service Discovery

If you want to use Eureka for service discovery in a microservices environment, follow these steps:

### Option 1: Use Existing Eureka Server

Set the environment variable in `.env`:
```bash
EUREKA_SERVER_URL=http://<eureka-host>:8761/eureka
SERVER_HOST=<your-service-hostname>
SERVER_PORT=8001
```

Example for Docker network:
```bash
EUREKA_SERVER_URL=http://eureka-server:8761/eureka
SERVER_HOST=user-service
SERVER_PORT=8001
```

### Option 2: Add Eureka to docker-compose.yml

Add this service to `docker-compose.yml`:

```yaml
eureka-server:
  image: steeltoe/config-server:latest
  # OR use Netflix Eureka: 
  # image: gcr.io/gke-release/eureka-server:latest
  container_name: eureka-server
  ports:
    - "8761:8761"
  environment:
    SPRING_CLOUD_CONFIG_SERVER_GIT_URI: https://github.com/spring-cloud-samples/config-repo
  networks:
    - timesmart-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8761/eureka/apps"]
    interval: 30s
    timeout: 10s
    retries: 3
```

Then update the `userservice` configuration:

```yaml
environment:
  - EUREKA_SERVER_URL=http://eureka-server:8761/eureka
  - SERVER_HOST=user-service
  - SERVER_PORT=8001
```

### Option 3: Run Local Eureka Server (Development)

Download and run Netflix Eureka locally:
1. [Download Eureka Server](https://cloud.spring.io/spring-cloud-netflix/2.1.x/spring-cloud-netflix.html)
2. Start it: `java -jar eureka-server.jar`
3. Access at http://localhost:8761/eureka
4. Set in `.env`: `EUREKA_SERVER_URL=http://localhost:8761/eureka`

---

## Verification

### Check if Eureka is Enabled

Look at the startup logs:

**Eureka Disabled (Default)**:
```
INFO:app.discovery.eureka_client:Eureka service discovery is disabled (EUREKA_SERVER_URL not configured)
```

**Eureka Enabled and Registered**:
```
INFO:app.discovery.eureka_client:Registered 'user-management-service' with Eureka at http://eureka-server:8761/eureka
```

**Eureka Enabled but Server Unavailable**:
```
ERROR:app.discovery.eureka_client:Eureka register error: ... (Eureka server may be unavailable at http://eureka-server:8761/eureka)
WARNING:app.main:Eureka registration failed; service will continue without discovery
```

### Check Service Instance (if Eureka is Running)

```bash
curl http://localhost:8761/eureka/apps/USER-MANAGEMENT-SERVICE
```

This should return the registered service instance if Eureka is enabled and running.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "All connection attempts failed" | Eureka server not running | Start Eureka or set `EUREKA_SERVER_URL=""` to disable |
| "Connection refused" | Wrong Eureka host/port | Verify `EUREKA_SERVER_URL` is correct |
| Service not visible in Eureka | Wrong `SERVER_HOST` | Use container name for Docker, actual hostname for bare metal |
| "Address already in use" | Port conflict | Change `SERVER_PORT` in docker-compose |

---

## Architecture Notes

### Without Eureka (Current Default)
- Services use hardcoded URLs in `config.py` (e.g., `ENTITY_CLIENT_URL=http://localhost:8003`)
- Simple, suitable for development and small deployments
- No automatic service discovery

### With Eureka
- Services self-register and heartbeat to Eureka
- Other services query Eureka to find service instances
- Requires adding service discovery client calls to client code
- Suitable for large microservices deployments

---

## Environment Variables Reference

```
# Eureka Configuration
EUREKA_SERVER_URL=http://eureka-server:8761/eureka  # Leave empty to disable
SERVICE_NAME=user-management-service                # Service identifier in Eureka
SERVER_HOST=user-service                            # Hostname as reachable by Eureka
SERVER_PORT=8001                                    # Port exposed in docker-compose
EUREKA_HEARTBEAT_INTERVAL=30                        # Seconds between heartbeats
```
