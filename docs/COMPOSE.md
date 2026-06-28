# Compose de la solution

Il est possible d'utiliser docker compose pour lancer la solution. Il est possible de lancer la solution en mode production ou en mode développement.
Fichier prod : compose.yml
Fichier dev : compose.local.yml

## Utilisation de compose.yml

En production, le compose se situe sur le serveur et un job jenkins se charge de le lancer.

```bash
docker compose -f compose.yml up -d
docker compose -f compose.yml logs -f backend
docker compose -f compose.yml down            # garde la DB
docker compose -f compose.yml down -v         # reset la DB
```

## Utilisation de compose.local.yml

### Lancer tous les services en arrière plan
```bash
docker compose -f compose.local.yml up -d
docker compose -f compose.local.yml logs -f backend
docker compose -f compose.local.yml down            # garde la DB
docker compose -f compose.local.yml down -v         # reset la DB
```

### Lancer un service en particulier
```bash
docker compose -f compose.local.yml up -d postgres
docker compose -f compose.local.yml logs -f postgres
docker compose -f compose.local.yml down postgres
```