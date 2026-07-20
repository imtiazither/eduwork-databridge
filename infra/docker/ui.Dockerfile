FROM node:24-alpine AS build
WORKDIR /app
COPY apps/reviewer-ui/package.json apps/reviewer-ui/package-lock.json ./
RUN npm ci
COPY apps/reviewer-ui ./
RUN npm run build

FROM nginx:1.29-alpine
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
