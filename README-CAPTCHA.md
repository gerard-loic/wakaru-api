L'endpoint POST /users/register est en place et protégé par un captcha Cloudflare Turnstile (gratuit, sans puzzle à résoudre pour l'utilisateur). Je l'ai testé sur le conteneur et tout fonctionne.

Ce qui a été ajouté
custom/entities/user/routes.py : la route est publique (mark_public). Le formulaire n'accepte que email, first_name, last_name, password (8 caractères minimum) et captcha_token. Tout autre champ est rejeté, par exemple roles ou level_id.
custom/entities/user/methods.py : register() impose le rôle USER et le niveau par défaut (levels.is_default). Un email déjà utilisé renvoie une 409 au lieu d'une 500. Le reste passe par votre create() existant, donc l'utilisateur reçoit ses connaissances par défaut et l'email de bienvenue.
custom/libs/captchahelper.py : vérifie le jeton auprès de Cloudflare avec la clé secrète. Si la clé est absente ou si Cloudflare ne répond pas, l'inscription est refusée. hCaptcha et reCAPTCHA fonctionnent de la même façon : il suffit de changer WAKARU_CAPTCHA_VERIFY_URL.
.env.exemple : ajout de WAKARU_CAPTCHA_SECRET et WAKARU_CAPTCHA_VERIFY_URL.
Résultats des tests
Cas	Réponse
Inscription valide	200, rôle USER, niveau N5, connaissances créées (hiragana, katakana, contenu du dernier thème)
Même email en majuscules	409
Champ roles ajouté au formulaire	422
Mot de passe trop court ou captcha vide	422
J'ai supprimé le compte de test ensuite.

Ce que j'ai modifié dans votre environnement local :

J'ai ajouté à votre .env la clé secrète de test de Cloudflare, qui valide tous les jetons. À remplacer par la vraie clé en production.
J'ai recréé le conteneur avec docker compose up -d, parce que docker restart ne relit pas le .env.
Côté front
Créez un widget Turnstile dans le dashboard Cloudflare. Vous obtenez une clé publique (site key) pour le front et une clé secrète pour WAKARU_CAPTCHA_SECRET.
Intégrez le widget dans la page d'inscription :

<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<div class="cf-turnstile" data-sitekey="VOTRE_SITE_KEY"></div>

const captcha_token = document.querySelector('[name="cf-turnstile-response"]').value;
await fetch('/users/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, first_name, last_name, password, captcha_token }),
});
// En cas d'erreur, réinitialiser le widget : turnstile.reset()
Un jeton n'est valable qu'une fois et pendant 5 minutes. Après une erreur (409, 422…), il faut donc réinitialiser le widget avant un nouvel essai. En développement, la clé publique de test 1x00000000000000000000AA affiche un widget qui passe toujours.

Pour aller plus loin (non fait)
Limiter le nombre de requêtes par IP, au niveau de Traefik (middleware rateLimit) ou avec slowapi. Le captcha ne protège pas de tout.
Vérifier l'adresse email avant d'activer le compte. Aujourd'hui, le compte est utilisable tout de suite.
Exposition MCP : si vous activez MCP, le serveur affiche toujours les routes publiques comme outils. /users/register en ferait partie, sauf si vous l'ajoutez à SYLO_MCP_EXCLUDE_FILE.
La 409 révèle qu'un email a déjà un compte. C'est courant pour une inscription, et le captcha lim