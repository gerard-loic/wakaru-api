# Commandes du projet

Toutes les commandes se lancent depuis la racine du projet.

- **Commandes applicatives** : elles s'exécutent dans le conteneur, qui doit être démarré, avec `make cmd c="<commande> [options]"`.
- **Commandes Docker et Traefik** : elles se lancent directement avec `make <cible>`.

Dans `c="..."`, une valeur avec des espaces se met entre apostrophes :

```bash
make cmd c="create_role --name 'Super admin' --uid SUPERADMIN"
```

Chaque commande applicative affiche son aide avec `--help`, et `make help` liste les cibles `make`.

> Les commandes utilisent le `.env` du projet : la base et le serveur SMTP qu'il indique sont ceux réellement utilisés. Avant une écriture ou un envoi, lancer `--dry-run` quand la commande le propose.

## Récapitulatif

| Commande | Rôle | Écrit en base | Envoie des mails | `--dry-run` |
| --- | --- | --- | --- | --- |
| `activate_new_theme` | Active le dernier thème créé et l'annonce | Oui | Oui | Oui |
| `delete_theme` | Supprime définitivement un thème et son contenu | Oui | Non | Oui |
| `create_user` | Crée un utilisateur | Oui | Oui | Oui |
| `create_role` | Crée un rôle | Oui | Non | Oui |
| `sync_permissions` | Crée les permissions manquantes | Oui | Non | Oui |
| `assign_permissions` | Associe des permissions à un rôle | Oui | Non | Oui |
| `generate_entities` | Génère les entités depuis la base | Non (écrit des fichiers) | Non | Oui |
| `generate_bruno_collection` | Génère une collection Bruno | Non (écrit un zip) | Non | Non |

## Commandes du projet Wakaru

### activate_new_theme

Active le dernier thème créé pour les utilisateurs non supprimés du rôle `USER` :

1. renseigne `publicated_at` sur le thème, s'il ne l'est pas déjà ;
2. crée leurs `user_knowledge` sur le thème et son contenu, ainsi que leur programme. Les éléments déjà connus gardent leur progression ;
3. envoie le mail `new_theme`, un mail individuel par utilisateur, à ceux dont `is_mailing_allowed` est vrai. Il contient le lien de désinscription : `WAKARU_UNSUBSCRIBE_SECRET` doit être renseigné, sinon la commande s'arrête avant toute modification.

| Option | Description |
| --- | --- |
| `--dry-run` | Ne modifie rien et n'envoie rien : affiche le thème, la publication, le sujet, l'image et le nombre de destinataires. |
| `--test-to EMAIL` | N'active rien et envoie uniquement à cette adresse, qui sera ensuite ignorée lors de l'envoi réel. |

```bash
make cmd c="activate_new_theme --dry-run"
make cmd c="activate_new_theme --test-to moi@exemple.fr"
make cmd c="activate_new_theme"
```

Un échec n'interrompt pas l'envoi. Les adresses qui ont déjà reçu la même annonce (même destinataire et même sujet dans `sendmails`) sont ignorées : relancer la commande ne renvoie qu'aux adresses en échec, sans changer la date de publication ni la progression des utilisateurs.

### delete_theme

Supprime **définitivement** un thème, en une seule transaction :

1. ses phrases et leurs tokens, ses règles de grammaire, ses exercices et leurs items ;
2. son vocabulaire (`theme_words`, `theme_kanji`) ;
3. ses mots et leurs compositions, ainsi que ses kanjis, sauf ceux utilisés par un autre thème ;
4. les `user_knowledge` de tout ce qui est supprimé, programme du thème compris.

| Option | Description |
| --- | --- |
| `--id ID` | Obligatoire. Id du thème. |
| `--dry-run` | Ne modifie rien : affiche le nombre de lignes concernées par table. |
| `--yes` | Ne demande pas de confirmation. Sans cette option, il faut saisir l'id du thème. |

```bash
make cmd c="delete_theme --id 12 --dry-run"
make cmd c="delete_theme --id 12"
```

Un mot ou un kanji partagé garde sa ligne et les `user_knowledge` de tous les utilisateurs. Les tokens de phrases d'autres thèmes qui pointaient vers un mot supprimé passent à `word_id` NULL et gardent leur `word_uid`. L'import les rattache si le mot revient.

Ne sont pas supprimés : le fichier image du thème dans `media/` et l'historique `sendmails`. `activate_new_theme` compare le sujet du mail : pour un thème réimporté sous le même nom, les adresses déjà servies seront donc ignorées.

## Commandes du core Sylo

### create_user

Crée un utilisateur avec le niveau marqué `is_default`, et lui associe éventuellement un rôle. Le comportement est le même que `POST /users` : avec un mot de passe, un mail de bienvenue est envoyé ; sans mot de passe, un mail d'initialisation est envoyé à la place.

| Option | Description |
| --- | --- |
| `--email EMAIL` | Obligatoire. Email de l'utilisateur. |
| `--first_name PRENOM` | Obligatoire. Prénom. |
| `--last_name NOM` | Obligatoire. Nom. |
| `--password MOT_DE_PASSE` | Mot de passe en clair, haché avant écriture. |
| `--role-uid UID` | uid du rôle à associer, par exemple `ADMIN`. |
| `--dry-run` | N'écrit rien et n'envoie aucun mail. |

```bash
make cmd c="create_user --email a@b.fr --first_name Alice --last_name B --role-uid ADMIN --dry-run"
```

### create_role

Crée un rôle et, avec `--config-file`, lui associe les permissions listées dans `roles.<uid>`.

| Option | Description |
| --- | --- |
| `--name NOM` | Obligatoire. Nom du rôle. |
| `--uid UID` | Obligatoire. Identifiant unique du rôle. |
| `--config-file FICHIER` | Fichier JSON de configuration. |
| `--dry-run` | N'écrit rien en base. |

```bash
make cmd c="create_role --name Administrateur --uid ADMIN --config-file custom/config/generate-config.json"
```

### sync_permissions

Crée une permission pour chaque route et méthode qui n'en a pas encore. Ne modifie jamais une permission existante.

| Option | Description |
| --- | --- |
| `--exclude-route ROUTE` | Exclut une route entière. Répétable, ou plusieurs routes séparées par des virgules. |
| `--exclude ROUTE:METHODE` | Exclut une route et une méthode précises. Répétable, ou plusieurs paires séparées par des virgules. |
| `--config-file FICHIER` | Fichier JSON : `exclude.permissions` et `additionnal.permissions`. |
| `--dry-run` | N'écrit rien en base. |

```bash
make cmd c="sync_permissions --config-file custom/config/generate-config.json --dry-run"
```

### assign_permissions

Associe des permissions à un rôle existant : toutes par défaut, ou celles de `roles.<uid>` avec `--config-file`. Ne modifie jamais une association existante.

| Option | Description |
| --- | --- |
| `--role-uid UID` | Obligatoire. uid du rôle cible. |
| `--exclude-file FICHIER` | Fichier des routes à exclure, une entrée par ligne. |
| `--config-file FICHIER` | Fichier JSON de configuration. |
| `--dry-run` | N'écrit rien en base. |

```bash
make cmd c="assign_permissions --role-uid USER --config-file custom/config/generate-config.json --dry-run"
```

Formats acceptés dans `roles.<uid>`, pour `create_role` et `assign_permissions` :

| Format | Sélection |
| --- | --- |
| `*` | Toutes les permissions |
| `users/login:POST` | Une méthode d'une route |
| `users/login:*` | Toutes les méthodes d'une route |
| `KNOWLEDGE_UNLIMITED` | Une permission par son uid |

### generate_entities

Génère une entité CRUD dans `custom/entities/<nom>/` pour chaque table de la base, avec les relations déduites des clés étrangères. Les tables de `exclude.routes` et les entités du core sont ignorées.

| Option | Description |
| --- | --- |
| `--config-file FICHIER` | Fichier JSON : `exclude.routes`. |
| `--force` | Écrase `model.py`, `methods.py` et `routes.py` des entités déjà présentes dans `custom/entities/`. |
| `--dry-run` | N'écrit aucun fichier. |

```bash
make cmd c="generate_entities --config-file custom/config/generate-config.json --dry-run"
```

> `--force` écrase le code personnalisé des entités, par exemple les routes et méthodes spécifiques à Wakaru.

### generate_bruno_collection

Génère une collection Bruno au format zip à partir des routes de l'API.

| Option | Description |
| --- | --- |
| `--output FICHIER` | Chemin du zip (défaut : `sylo_api_bruno_collection.zip` à la racine du conteneur). |
| `--base-url URL` | Valeur par défaut de `baseUrl` (défaut : `http://localhost:8000`). |
| `--collection-name NOM` | Nom de la collection (défaut : `Sylo API`). |

```bash
make cmd c="generate_bruno_collection --output logs/wakaru_bruno.zip --base-url http://wakaru-api.diatem.local --collection-name Wakaru"
```

> Seuls `custom/`, `logs/` et `media/` sont partagés avec la machine hôte. Sans `--output` vers l'un de ces dossiers, le zip reste dans le conteneur.

## Commandes make

### Conteneurs

| Commande | Rôle |
| --- | --- |
| `make up` | Crée le réseau Traefik si besoin, récupère l'image et démarre les conteneurs. |
| `make down` | Arrête et supprime les conteneurs et le réseau du projet. |
| `make start` | Relance les services existants. |
| `make stop` | Arrête les services sans les supprimer. |
| `make pull` | Récupère la dernière version de l'image. |
| `make bash` | Ouvre un shell dans le conteneur. |
| `make network` | Crée le réseau Docker `traefik-network` s'il n'existe pas. |
| `make cmd c="..."` | Lance une commande applicative dans le conteneur. |
| `make help` | Liste les cibles disponibles. |

### Traefik

| Commande | Rôle |
| --- | --- |
| `make traefik-up` | Démarre Traefik en local (HTTP, dashboard sur le port 8080). |
| `make traefik-down` | Arrête Traefik en local. |
| `make traefik-logs` | Suit les logs de Traefik en local. |
| `make traefik-prod-up` | Démarre Traefik en production (HTTPS et Let's Encrypt). |
| `make traefik-prod-down` | Arrête Traefik en production. |

## Ajouter une commande

Un fichier `custom/scripts/<commande>.py` devient disponible sous le nom `<commande>`. À nom égal, il remplace le script du core. Voir [custom/README.md](custom/README.md).
