# Image de production de TOB-MAQ : site + API dans un seul conteneur.
FROM node:22-alpine
WORKDIR /app
COPY server/package.json server/package-lock.json server/
RUN cd server && npm ci --omit=dev && npm cache clean --force
COPY index.html ./
COPY ressources ressources
COPY apercus apercus
COPY icones icones
COPY pwa pwa
COPY videos videos
COPY server/src server/src
# /data contient la base SQLite et les fichiers envoyés : à monter sur un volume persistant.
# Les volumes de Render et Railway sont montés au nom de root : le processus doit pouvoir y écrire.
RUN mkdir -p /data
ENV NODE_ENV=production PORT=8080 STORAGE_DIR=/data TRUST_PROXY=1
VOLUME /data
EXPOSE 8080
CMD ["node", "--disable-warning=ExperimentalWarning", "server/src/index.js"]
