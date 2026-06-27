# Compose de la solution

Il est possible d'utiliser docker compose pour lancer la solution. Il est possible de lancer la solution en mode production ou en mode développement.
Fichier prod : compose.yml
Fichier dev : compose.local.yml

## Utilisation de compose.local.yml
```bash
docker compose -f compose.local.yml up -d
docker compose -f compose.local.yml logs -f backend
docker compose -f compose.local.yml down            # garde la DB
docker compose -f compose.local.yml down -v         # reset la DB
```