FROM node:16-alpine

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy application code
COPY frontend/ .

# Build frontend
RUN npm run build

# Serve using nginx
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html 