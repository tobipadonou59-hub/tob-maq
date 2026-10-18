# Image de production de l'assistant WhatsApp.
FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY src src
COPY public public
COPY regles.json ./
RUN mkdir -p /data
ENV NODE_ENV=production PORT=8080 STORAGE_DIR=/data TRUST_PROXY=1
VOLUME /data
EXPOSE 8080
CMD ["node", "--disable-warning=ExperimentalWarning", "src/index.js"]
