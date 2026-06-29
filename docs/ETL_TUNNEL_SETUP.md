# Setup du tunnel SSH vers Postgres VPS

Ce document décrit comment configurer un accès au Postgres hébergé sur le VPS
depuis une machine locale exécutant la pile Airflow/Kafka (`compose_etl.yml`).

## Contexte

La pile ETL (Airflow, Kafka, producers) tourne en local pour des raisons de
ressources (le VPS n'a que 8 Go de RAM, déjà occupés par Jenkins, Grafana,
MLflow, le registry et la stack applicative).

Les résultats produits par les DAGs Airflow doivent être écrits dans le Postgres
du VPS pour être consommés par le backend et l'API IA. La connexion passe par
un tunnel SSH local → VPS, sans exposer Postgres sur Internet.

```
┌─────────────────────────┐      tunnel SSH       ┌────────────────────────┐
│  Machine locale         │  ─────────────────►   │  VPS ecluse.cloud      │
│                         │   127.0.0.1:5433      │                        │
│  - Airflow (Docker)     │   →                   │  - Postgres :5432      │
│  - Kafka                │   localhost:5432      │  - backend, api_ia     │
│  - autossh / systemd    │                       │  - Jenkins, Grafana…   │
└─────────────────────────┘                       └────────────────────────┘
```

## Prérequis

- Linux ou macOS (Windows : utiliser WSL2)
- OpenSSH client installé
- Avoir demandé l'accès à l'admin du projet en lui envoyant une clé publique
  (voir étape 1)

## 1. Générer une clé SSH dédiée au tunnel

Une clé par personne, séparée de la clé SSH personnelle. Ça permet de révoquer
l'accès d'un membre sans impacter les autres.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mecha_tunnel -N "" -C "mecha-etl-tunnel-$USER"
```

- `-t ed25519` : algorithme moderne, clés courtes
- `-f` : chemin de la clé
- `-N ""` : pas de passphrase (nécessaire pour un service automatisé)
- `-C` : commentaire identifiant la clé dans `authorized_keys`

## 2. Envoyer la clé publique à l'admin

Récupérer le contenu de la clé **publique** (jamais la privée) :

```bash
cat ~/.ssh/mecha_tunnel.pub
```

Envoyer la ligne complète à l'admin (Slack, Discord, email — c'est une clé
publique, aucun risque). L'admin l'ajoute au VPS avec les restrictions
appropriées (`restrict,permitopen="127.0.0.1:5432"`).

## 3. Tester la connexion manuelle

Une fois la clé ajoutée côté VPS, tester le tunnel :

```bash
ssh -i ~/.ssh/mecha_tunnel \
    -o IdentitiesOnly=yes \
    -o PasswordAuthentication=no \
    -N \
    -L 127.0.0.1:5433:localhost:5432 \
    deploy@ecluse.cloud
```

Explication des options :

- `-i` : utiliser cette clé spécifique
- `IdentitiesOnly=yes` : n'essayer que cette clé (évite "too many auth failures"
  si ssh-agent propose d'autres clés)
- `PasswordAuthentication=no` : pas de fallback mot de passe (évite de
  déclencher fail2ban en cas d'échec)
- `-N` : pas de commande, juste le tunnel
- `-L 127.0.0.1:5433:localhost:5432` : forwarder le port local 5433 vers le
  port 5432 du VPS

Si la commande reste ouverte sans rien afficher, le tunnel fonctionne. Tester
depuis un autre terminal :

```bash
nc -zv 127.0.0.1 5433
# Attendu : Connection to 127.0.0.1 5433 port [tcp/*] succeeded!
```

Couper le tunnel manuel (Ctrl+C) une fois le test concluant.

## 4. Installer le service systemd

Le tunnel doit être permanent et résister aux coupures réseau / reboots. On
utilise `autossh` géré par `systemd`. Voir [`systemd-tunnel.md`](./SYSTEMD_TUNNEL.md).

## 5. Configuration côté Airflow

Dans `compose_etl.yml`, les services Airflow doivent pointer vers le tunnel
plutôt que vers un Postgres local pour la base `industrial_dw` :

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"   # nécessaire sous Linux
environment:
  AIRFLOW_CONN_INDUSTRIAL_POSTGRES: postgres://etl_writer:<password>@host.docker.internal:5433/<db>?options=-csearch_path%3Dindustrial_dw
```

Les conteneurs Airflow joignent l'hôte via `host.docker.internal` et tapent sur
le port 5433, qui est le débouché local du tunnel. La requête sort ensuite par
SSH jusqu'au Postgres du VPS.

La base de métadonnées Airflow elle-même (`airflow`) reste sur le Postgres
local — pas besoin de la mettre sur le VPS, elle a un fort taux d'écriture et
n'a pas d'intérêt à être centralisée.

## Vérification de l'état

```bash
# Service systemd up ?
sudo systemctl status mecha-tunnel.service

# Port local ouvert ?
nc -zv 127.0.0.1 5433

# Connexion Postgres OK ?
psql -h 127.0.0.1 -p 5433 -U etl_writer -d <db>
```

## Révocation d'un accès

Côté VPS, supprimer la ligne correspondante de `~/.ssh/authorized_keys` du
user `deploy` :

```bash
ssh deploy@ecluse.cloud
sed -i.bak '/mecha-etl-tunnel-<prenom>/d' ~/.ssh/authorized_keys
```

Le `.bak` permet de revenir en arrière en cas d'erreur.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `Permission denied (publickey)` | Clé non ajoutée côté VPS, ou permissions `~/.ssh` incorrectes côté VPS (doit être `700`, `authorized_keys` en `600`) |
| `Connection refused` sur port 22 | Fail2ban a banni l'IP après trop d'échecs. Attendre ~10 min ou se déban depuis une autre IP |
| `Connection refused` sur 5433 | Tunnel non démarré, vérifier `systemctl status mecha-tunnel` |
| Le tunnel marche puis tombe | Vérifier `journalctl -u mecha-tunnel -f` ; normalement autossh relance tout seul |