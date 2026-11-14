# Miroir Lemmyverse pour zAppLemmy

Ce dépôt public contient seulement le script de synchronisation, son workflow GitHub Pages et deux snapshots publics d’amorçage issus de Lemmyverse. Il ne contient ni les sources de l’application ni ses données privées.

Le miroir est publié sur https://pierre121.github.io/lemmyverse-mirror/ et fournit `data/{instances,communities}.{previous,latest}.json`. Les tables sont téléchargées et validées chaque lundi à 03:17 UTC ; une exécution manuelle est également possible dans Actions. Un échec de téléchargement ou de validation conserve le site déjà publié. Le snapshot `previous` reprend le dernier snapshot `latest` publié.

Source : https://data.lemmyverse.net/data/json-bundle.zip (projet https://github.com/tgxn/lemmy-explorer). Aucun fichier média n’est téléchargé. Les images et descriptions présentes dans les tables restent des champs JSON ; aucun octet d’image n’est conservé séparément.

Commande : `python scripts/miroirLemmyverse.py --pages-base https://pierre121.github.io/lemmyverse-mirror --output _site`.

Maintenance GitHub : les workflows planifiés des dépôts publics peuvent être désactivés après 60 jours sans activité du dépôt. Si la date de `data/index.json` ne progresse plus, vérifier Actions et réactiver le workflow. Voir https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows.
