# Service systemd pour le tunnel ETL

Documente la mise en place d'un service `systemd` géré par `autossh` qui
maintient le tunnel SSH vers le Postgres du VPS de façon permanente.

Prérequis : avoir réalisé les étapes 1 à 3 de [`etl-tunnel-setup.md`](./etl-tunnel-setup.md)
(clé générée, ajoutée côté VPS, tunnel manuel testé).

## Pourquoi autossh + systemd

`ssh -N -L ...` lancé à la main ne suffit pas en production :

- il s'arrête si le terminal est fermé
- il ne se relance pas après une coupure réseau
- il ne survit pas à un reboot de la machine

`autossh` détecte les connexions mortes et les relance. `systemd` garantit le
démarrage au boot et le redémarrage en cas de crash du process autossh
lui-même. La combinaison des deux donne un tunnel résilient à trois niveaux
(coupure réseau, crash autossh, reboot machine).

## Installation d'autossh

```bash
sudo apt install autossh   # Debian/Ubuntu
# ou
brew install autossh       # macOS
```

## Création du service

Créer le fichier `/etc/systemd/system/mecha-tunnel.service` :

```ini
[Unit]
Description=SSH tunnel to MECHA VPS Postgres
After=network-online.target
Wants=network-online.target

[Service]
User=<ton-user-local>
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh \
  -M 0 \
  -N \
  -o "ServerAliveInterval=30" \
  -o "ServerAliveCountMax=3" \
  -o "ExitOnForwardFailure=yes" \
  -o "StrictHostKeyChecking=accept-new" \
  -o "IdentitiesOnly=yes" \
  -o "PasswordAuthentication=no" \
  -i /home/<ton-user-local>/.ssh/mecha_tunnel \
  -L 127.0.0.1:5433:localhost:5432 \
  deploy@ecluse.cloud
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Remplacer `<ton-user-local>` par ton nom d'utilisateur Linux (deux occurrences :
`User=` et le chemin de la clé).

### Détail des options

| Option | Rôle |
|---|---|
| `After/Wants=network-online.target` | Ne démarre pas avant que le réseau soit prêt |
| `AUTOSSH_GATETIME=0` | autossh ne considère pas un échec immédiat comme bloquant ; il réessaie indéfiniment |
| `-M 0` | Désactive le monitoring port d'autossh (redondant avec `ServerAliveInterval`) |
| `-N` | Pas de commande à exécuter, juste le tunnel |
| `ServerAliveInterval=30` | Envoie un ping SSH toutes les 30s |
| `ServerAliveCountMax=3` | Considère la connexion morte après 3 pings sans réponse (≈90s) |
| `ExitOnForwardFailure=yes` | Sort si le port forward ne s'établit pas (ex. port déjà pris localement). systemd relance proprement. |
| `StrictHostKeyChecking=accept-new` | Accepte automatiquement le host key au premier démarrage, mais refuse les changements ensuite (protection MITM) |
| `IdentitiesOnly=yes` | N'essaie que la clé fournie par `-i`, pas celles de ssh-agent |
| `PasswordAuthentication=no` | Pas de fallback mot de passe (évite fail2ban en cas d'échec d'auth) |
| `Restart=always` + `RestartSec=10` | Si autossh crashe malgré tout, systemd le relance après 10s |

## Activation

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mecha-tunnel.service
```

`enable --now` fait deux choses :

- `enable` : démarrage automatique au boot
- `--now` : démarre le service immédiatement aussi

## Vérification

```bash
# Statut du service (doit être "active (running)")
sudo systemctl status mecha-tunnel.service

# Logs récents
sudo journalctl -u mecha-tunnel.service -n 50

# Port local ouvert
nc -zv 127.0.0.1 5433
```

## Tests de robustesse

À faire au moins une fois après installation. Ces tests valident que le tunnel
résiste aux pannes courantes — utile à mentionner en soutenance comme preuve
de tolérance aux pannes.

### Test 1 : coupure réseau

```bash
# Couper le wifi pendant 20s puis le rallumer
sudo journalctl -u mecha-tunnel.service -f
# Attendre, observer la reconnexion
nc -zv 127.0.0.1 5433
```

Le tunnel doit se rétablir tout seul en moins d'une minute.

### Test 2 : crash autossh

```bash
# Tuer le process autossh
sudo pkill autossh
sleep 15
sudo systemctl status mecha-tunnel.service
```

systemd doit avoir relancé le service automatiquement (visible dans le statut :
`Active: active (running)` avec un uptime récent).

### Test 3 : reboot

```bash
sudo reboot
# Au retour, sans rien lancer manuellement :
sudo systemctl status mecha-tunnel.service
nc -zv 127.0.0.1 5433
```

Le tunnel doit être actif sans intervention.

## Commandes utiles

```bash
# Arrêter le tunnel temporairement
sudo systemctl stop mecha-tunnel.service

# Le redémarrer
sudo systemctl restart mecha-tunnel.service

# Désactiver complètement (ne se relancera plus au boot)
sudo systemctl disable --now mecha-tunnel.service

# Suivre les logs en temps réel
sudo journalctl -u mecha-tunnel.service -f
```

## Dépannage

| Erreur dans les logs | Cause / solution |
|---|---|
| `bind: Address already in use` | Le port 5433 local est déjà pris (peut-être par un autre tunnel ou un Postgres local). Changer le port côté `-L` et côté Airflow. |
| `Permission denied (publickey)` | Clé non acceptée côté VPS. Vérifier `authorized_keys` du user `deploy`. |
| `kex_exchange_identification: read: Connection reset by peer` | Souvent fail2ban côté VPS. Voir [`etl-tunnel-setup.md`](./etl-tunnel-setup.md) section dépannage. |
| Le service est actif mais `nc` échoue | `ExitOnForwardFailure=yes` est censé éviter ça. Vérifier `journalctl` pour comprendre pourquoi le forward n'est pas effectif. |

## Architecture finale validée

Une fois ce service en place sur chaque machine de l'équipe qui a besoin
d'écrire dans le DW :

- chaque membre a sa propre clé (`mecha-etl-tunnel-<prenom>`) avec restrictions
  `restrict,permitopen="127.0.0.1:5432"`
- les connexions sont traçables dans les logs sshd du VPS
- la révocation d'un accès est unitaire (suppression d'une ligne)
- le tunnel survit aux coupures réseau et aux reboots
- Postgres n'est pas exposé sur Internet

Ces propriétés répondent directement aux critères "architecture stable,
efficace, pérenne" et "tolérance aux pannes" du Bloc 4.