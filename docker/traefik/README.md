# Traefik (reverse-proxy)

Traefik est le point d'entree HTTP(S) unique. Il decouvre les conteneurs via
leurs `labels` Docker et route vers eux. Tous les conteneurs exposes (Traefik +
apps) partagent le reseau Docker externe `traefik-network`.

Le reseau est cree automatiquement par `make up` / `make traefik-up`
(cible `network` du Makefile), ou manuellement :

```bash
docker network create traefik-network
```

## Local

HTTP seul, dashboard sur http://localhost:8080

```bash
make traefik-up      # demarre Traefik
make up              # demarre l'app
make traefik-down    # arrete Traefik
```

Ajouter dans `/etc/hosts` :

```
127.0.0.1 wakaru-api.diatem.local
```

Puis http://wakaru-api.diatem.local

`docker/.env` doit contenir `COMPOSE_TRAEFIK_ENTRYPOINT=http`.

## Production (VPS)

HTTPS + Let's Encrypt automatique, redirection HTTP -> HTTPS.

Prerequis :

1. Les DNS du domaine (ex: `api.mondomaine.fr`) pointent vers l'IP du VPS.
2. Les ports 80 et 443 sont ouverts.
3. `docker/traefik/.env` cree depuis `.env.exemple` (renseigner `TRAEFIK_ACME_EMAIL`).
4. `docker/.env` avec :
   - `COMPOSE_PROJECT_HOST=api.mondomaine.fr`
   - `COMPOSE_TRAEFIK_ENTRYPOINT=https`
   - `COMPOSE_RESTART_POLICY=unless-stopped`

```bash
make traefik-prod-up   # demarre Traefik (prod)
make up                # demarre l'app
```

Les certificats sont stockes dans le volume Docker `traefik_traefik-letsencrypt`.
