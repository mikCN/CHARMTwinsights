# Docker Tips for CHARMTwinsights

This guide provides Docker troubleshooting help for team members who are new to Docker.

## Common Issues and Solutions

### "Cannot connect to the Docker daemon"
- **Solution:** Make sure Docker Desktop is running. On Mac/Windows, look for the Docker icon in your system tray.
- **Check:** Run `docker --version` to verify Docker is installed and accessible.

### "Port already in use" or "address already in use"
- **Cause:** Another application or previous Docker container is using the same port.
- **Solution:** Stop the application using the port, or stop all Docker containers:
  ```bash
  docker compose down
  # If that doesn't work:
  docker stop $(docker ps -q) 2>/dev/null || echo "No containers to stop"
  ```

### "Build failed" or "No space left on device"
- **Cause:** Docker has run out of disk space.
- **Solution:** Clean up unused Docker resources:
  ```bash
  # Safe cleanup (removes unused images/containers)
  docker system prune
  
  # More aggressive cleanup (removes everything not currently running)
  docker system prune -a
  ```

### "Models not found" or "Model registration failed"
- **Cause:** Model images weren't built properly.
- **Solution:** Rebuild everything from scratch:
  ```bash
  docker compose down
  ./build_all.sh --no-cache
  docker compose up --detach
  ```

### "Service unhealthy" or "Connection refused"
- **Cause:** Services are starting up in the wrong order or failing health checks.
- **Solution:** Wait longer for startup (can take 1-2 minutes), or check logs:
  ```bash
  # Check what's happening
  docker compose logs
  
  # Check specific service
  docker compose logs model_server
  
  # Restart if needed
  docker compose restart
  ```

### "Permission denied" (Linux/Mac)
- **Cause:** Docker needs elevated permissions or user isn't in docker group.
- **Solution:** 
  - Try with `sudo`: `sudo docker compose up --detach`
  - Or add your user to docker group: `sudo usermod -aG docker $USER` (requires logout/login)

## Getting Help

1. **Check service status:** `docker compose ps`
2. **View logs:** `docker compose logs [service_name]`
3. **Check what's running:** Use `scripts/docker_status.sh`
4. **Start fresh:** `docker compose down && ./build_all.sh && docker compose up --detach`

If you're still having trouble, include the output of `docker compose logs` when asking for help.

## Advanced Docker Commands (Use with Caution)

These commands are more powerful but can affect other Docker projects on your system:

```bash
# Remove all stopped containers and unused networks (safe)
docker system prune

# Remove ALL unused Docker resources including images (more aggressive)
docker system prune -a

# Stop all running containers (affects ALL Docker projects)
docker stop $(docker ps -q)

# Remove all containers (affects ALL Docker projects)  
docker rm $(docker ps -aq)
```

**When to use these:** Only if you're having persistent issues and `docker compose down` isn't working. These commands affect your entire Docker installation, not just CHARMTwinsights.

## Understanding Docker Compose Commands

### Safe Commands (only affect CHARMTwinsights)
- `docker compose ps` - show status of CHARMTwinsights services
- `docker compose logs` - show logs for CHARMTwinsights services
- `docker compose down` - stop CHARMTwinsights services
- `docker compose up` - start CHARMTwinsights services
- `docker compose restart` - restart CHARMTwinsights services

### System-wide Commands (affect all Docker projects)
- `docker ps` - show all running containers
- `docker stop $(docker ps -q)` - stop all containers
- `docker system prune` - clean up unused Docker resources
- `scripts/docker_clean.sh` - nuclear option (removes everything)

## When Things Go Really Wrong

If you're seeing persistent issues that the above steps don't fix:

1. **First try:** `docker compose down && ./build_all.sh --no-cache && docker compose up --detach`

2. **If that fails:** Check if Docker Desktop has enough resources allocated:
   - On Mac: Docker Desktop > Settings > Resources
   - Increase Memory to at least 4GB, Disk to at least 20GB

3. **Nuclear option:** `scripts/docker_clean.sh` (removes ALL Docker containers/networks on your system)

4. **Get help:** Share the output of `docker compose logs` when asking for support
