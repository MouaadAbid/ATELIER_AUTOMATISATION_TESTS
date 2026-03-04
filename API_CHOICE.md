# API Choice

- **Étudiant :** ABID Mouaad
- **API choisie :** Frankfurter (taux de change)
- **URL base :** `https://api.frankfurter.app`
- **Documentation officielle :** https://www.frankfurter.app/docs/
- **Auth :** None

## Endpoints testés

- `GET /latest?from=EUR` — Taux de change EUR vers toutes devises
- `GET /latest?from=EUR&to=USD,GBP` — Taux EUR → USD et GBP
- `GET /2024-01-01?from=EUR&to=USD` — Taux historique à une date précise
- `GET /currencies` — Liste de toutes les devises disponibles
- `GET /latest?from=INVALID` — Cas invalide → 422 attendu
- `GET /9999-99-99` — Date invalide → 404 ou 422 attendu

## Hypothèses de contrat

| Endpoint | Champ attendu | Type | Code HTTP |
|---|---|---|---|
| `/latest` | `amount` | float | 200 |
| `/latest` | `base` | string | 200 |
| `/latest` | `date` | string (YYYY-MM-DD) | 200 |
| `/latest` | `rates` | object | 200 |
| `/currencies` | objet clé-valeur string | object | 200 |
| `/latest?from=INVALID` | réponse d'erreur | — | 422 |

## Limites / Rate limiting connu

- Pas de rate limit documenté officiel mais usage raisonnable recommandé.
- L'API est gratuite et sans clé, maintenue par la communauté.
- Les données sont mises à jour chaque jour ouvrable (pas de WE/jours fériés).

## Risques

- **Instabilité** : API open-source maintenue bénévolement, downtime possible.
- **Données manquantes** : Certaines dates (weekends, jours fériés) retournent la date du dernier jour ouvrable.
- **CORS** : Non applicable (appels server-side).
- **Lat. variable** : Possible latence élevée selon charge serveur.
