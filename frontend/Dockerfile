FROM node:24.11.0-alpine AS build
WORKDIR /app
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
ARG VITE_AMAP_KEY
ARG VITE_AMAP_SECURITY_CODE
ENV VITE_AMAP_KEY=$VITE_AMAP_KEY
ENV VITE_AMAP_SECURITY_CODE=$VITE_AMAP_SECURITY_CODE
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.29.5-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
