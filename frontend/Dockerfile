FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

# Variante oficial que roda sem root, por isso a porta 8080 no lugar da 80.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
