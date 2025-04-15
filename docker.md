Each directory (frontend and backend) has its own Dockerfile because they're separate applications with different requirements:

1. **Backend Dockerfile** (in `/backend`):
   - Uses Python base image
   - Installs Chrome and other dependencies needed for scraping
   - Configures Python environment 
   - Sets up the API server

2. **Frontend Dockerfile** (in `/frontend`):
   - Uses Node.js for building the Next.js application
   - Compiles TypeScript and React components
   - Creates a production build of the frontend

This separation provides several advantages:
- Independent scaling (you can run multiple instances of either component)
- Separate deployment cycles
- Proper separation of concerns
- Smaller, more focused containers
- Different resource requirements (backend might need more CPU, frontend more memory)

Your docker-compose.yml ties these containers together, defining how they interact with each other and shared services like the database.
