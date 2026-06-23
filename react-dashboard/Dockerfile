FROM node:22-slim AS build
WORKDIR /app
COPY react-dashboard/package.json react-dashboard/package-lock.json ./
RUN npm install
COPY react-dashboard/ .
# VITE_API_URL vazio → client usa URLs relativas → nginx faz o proxy
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# template processado pelo nginx na inicializacao via envsubst (BACKEND_URL)
COPY react-dashboard/nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
