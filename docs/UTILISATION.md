# Utilisation

Travailler sur le repo : 

- Cloner le repo : `git clone <url-du-repo>`
- Créer une branche pour vos modifications : `git checkout -b feature/ma-feature`
- Ajouter vos modifications : `git add .`
- Faire vos modifications et les commiter : `git commit -m "Description de mes modifications"`
- Pousser vos modifications sur votre branche : `git push origin feature/ma-feature`

Merger vos modifications dans la branche principale (main) :

- Créer une Pull Request (PR) sur GitHub pour demander la fusion de votre branche dans main.
- Une fois la PR approuvée, vous pouvez la fusionner dans main.

Production :

- Le pipeline Jenkins se déclenche automatiquement sur la branche production pour déployer les modifications en production.