# Utilisation

Les branches de ce repo correspondent aux composants du projet. Pour chacun d'entre eux, le template est le suivant :
- `nom_du_composant` : branche de développement du composant
- `nom_du_composant/feature/nom_de_la_feature` : branche de développement d'une feature spécifique du composant
- `nom_du_composant/bugfix/description_du_bug` : branche de développement d'une correction de bug spécifique du composant
- `nom_du_composant/production` : branche de production du composant, c'est à partir d'elle que la pipeline de CI/CD est déclenchée pour le déploiement de l'application

Exemple :
- `backend` : branche de développement du backend
- `backend/feature/authentification` : branche de développement de la feature d'authentification du backend
- `backend/bugfix/correction_bogue_api` : branche de développement de la correction d'un bug spécifique de l'API du backend
- `backend/production` : branche de production du backend, c'est à partir d'elle que la pipeline de CI/CD est déclenchée pour le déploiement de l'application