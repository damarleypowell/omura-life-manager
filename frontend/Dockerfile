FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Render passes NEXT_PUBLIC_API_URL as an env var — bake it in at build time
ARG NEXT_PUBLIC_API_URL=https://omura-life-manager.onrender.com
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
