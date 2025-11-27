FROM node:20-alpine AS builder

WORKDIR /app

# Установка зависимостей
COPY package.json package-lock.json* ./
RUN npm ci

# Копирование кода и сборка
COPY . .
RUN npm run build

# Production образ
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Копируем только необходимые файлы из standalone сборки
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Запуск в production режиме (без HMR)
CMD ["node", "server.js"]

