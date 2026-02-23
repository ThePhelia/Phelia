# Stage 1 - install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2 - build the Vite app
FROM deps AS build
WORKDIR /app
ARG VITE_API_BASE=/api/v1
ARG VITE_WS_BASE=/ws
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_WS_BASE=${VITE_WS_BASE}
COPY . .
RUN npm run build

# Stage 3 - run static server
FROM nginx:1.27-alpine AS runner
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
