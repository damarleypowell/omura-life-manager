FROM node:20-alpine

WORKDIR /app

# Install deps
COPY package.json package-lock.json* ./
RUN npm install

# Copy app
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
