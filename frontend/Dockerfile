FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run dev server with host flag to allow external connections
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
