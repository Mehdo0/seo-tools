# SEO Inspector — Guide Utilisateur

> **SEO title** : « SEO Inspector — Chrome Extension SEO Gratuite | Analyse On-Page »  
> **SEO description** : « Analysez le SEO de n'importe quelle page en 1 clic. Méta-tags, mots-clés, structure, score. Gratuit. Extension Chrome Manifest V3. »

---

## 📖 Qu'est-ce que SEO Inspector ?

**SEO Inspector** est une extension Chrome qui analyse le référencement naturel (SEO) de n'importe quelle page web en un seul clic. Elle examine les balises meta, la structure des titres, les mots-clés, les liens, les images, les données structurées et la lisibilité, puis attribue un **score SEO sur 100**.

![SEO Inspector — aperçu de l'extension](screenshot-placeholder.png)

L'extension fonctionne en local dans votre navigateur et communique avec l'API backend pour produire un rapport complet en temps réel.

---

## ⚡ Installation

### Depuis le Chrome Web Store

1. Ouvrez le [Chrome Web Store](https://chromewebstore.google.com) et recherchez **« SEO Inspector »**
2. Cliquez sur **Ajouter à Chrome**
3. L'icône SEO Inspector apparaît dans la barre d'outils de votre navigateur

### Installation manuelle (mode développeur)

```bash
git clone https://github.com/votre-compte/seo-tools.git
cd seo-tools/extension
```

1. Ouvrez `chrome://extensions/` dans Chrome
2. Activez le **Mode développeur** (coin supérieur droit)
3. Cliquez sur **Charger l'extension non empaquetée**
4. Sélectionnez le dossier `seo-tools/extension/`

---

## 🆚 Free vs Premium

| Fonctionnalité | Gratuit | Premium (5 €/mois) |
|---|---|---|
| Analyse SEO On-Page | ✓ | ✓ |
| Score SEO /100 | ✓ | ✓ |
| Analyse des balises Meta | ✓ | ✓ |
| Analyse des titres (H1-H6) | ✓ | ✓ |
| Mots-clés (top 10) | ✓ | ✓ (top 20 + bigrammes/trigrammes) |
| Analyse des liens | ✓ | ✓ |
| Analyse des images (alt) | ✓ | ✓ |
| Rapport de lisibilité Flesch-Kincaid | ✗ | ✓ |
| Données structurées (Schema.org) | ✗ | ✓ |
| Viewport mobile check | ✗ | ✓ |
| Export CSV | ✗ | ✓ |
| Historique des analyses | ✗ | ✓ |
| Support prioritaire | ✗ | ✓ |
| Analyses/mois | 50 | Illimité |

---

## 🧭 Utilisation des onglets

L'interface de l'extension est organisée en 6 onglets, accessibles après avoir cliqué sur l'icône **SEO Inspector** dans la barre d'outils Chrome.

### 1. 📋 Overview

L'onglet **Overview** affiche un résumé global de l'analyse :

- **Score SEO** : une note sur 100 avec un code couleur (vert > 80, orange 50-79, rouge < 50)
- **Résumé** des forces et faiblesses principales
- **Badges** indiquant : présence d'un `viewport` mobile, données structurées détectées, canonical URL présente, etc.

*Conseil : commencez toujours par cet onglet pour avoir une vue d'ensemble avant de plonger dans les détails.*

### 2. 🏷️ Meta

L'onglet **Meta** détaille toutes les balises meta détectées :

| Balise | Description |
|---|---|
| **Title** | Titre de la page + longueur (idéal : 30-65 caractères) |
| **Description** | Meta description + longueur (idéal : 120-160 caractères) |
| **Open Graph** | `og:title`, `og:description`, `og:image`, `og:type` |
| **Twitter Cards** | `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image` |
| **Canonical** | URL canonique déclarée |
| **Robots** | Directives `robots` (index/noindex, follow/nofollow) |

*Bon à savoir : des balises Open Graph et Twitter Cards bien renseignées améliorent l'apparence de vos pages lors du partage sur les réseaux sociaux.*

### 3. 📑 Headings

L'onglet **Headings** affiche la hiérarchie des titres (H1 à H6) :

- Nombre de balises pour chaque niveau
- Contenu textuel de chaque titre (tronqué à 120 caractères)
- Alerte si plus d'un H1 ou si aucun H1 n'est présent

*Recommandation SEO : une seule balise H1 par page, contenant le mot-clé principal.*

### 4. 🔑 Keywords

L'onglet **Keywords** analyse la densité lexicale :

- **Top mots** : les 10 (gratuit) ou 20 (premium) mots les plus fréquents
- **Bigrammes** : paires de mots récurrentes (premium)
- **Trigrammes** : triplets de mots récurrents (premium)
- Filtrage automatique des stop words français et anglais

*Utilisez ces données pour vérifier que vos mots-clés cibles apparaissent en bonne position dans le contenu.*

### 5. 🔗 Links

L'onglet **Links** comptabilise les liens de la page :

- **Liens internes** : nombre de liens pointant vers le même domaine
- **Liens externes** : nombre de liens sortants
- **Total** : somme des deux

*Bon à savoir : les ancres `javascript:`, `#` et `mailto:` sont exclues du comptage.*

### 6. 🖼️ Images

L'onglet **Images** évalue l'accessibilité des images :

- **Total d'images** sur la page
- **Images sans attribut `alt`** (problème d'accessibilité et de SEO image)
- **Ratio d'images avec `alt`** (utilisé dans le calcul du score SEO)

*Recommandation : chaque image doit avoir un attribut `alt` descriptif contenant si possible le mot-clé cible.*

---

## 📊 Fonctionnalités Premium additionnelles

### Rapport de lisibilité Flesch-Kincaid

Disponible dans l'onglet **Overview** pour les utilisateurs premium. La formule de Flesch-Kincaid mesure la facilité de lecture du texte :

| Score FK | Niveau |
|---|---|
| 90-100 | Très facile |
| 80-89 | Facile |
| 70-79 | Assez facile |
| 60-69 | Standard |
| 50-59 | Assez difficile |
| 30-49 | Difficile |
| 0-29 | Très difficile |

### Données structurées (Schema.org)

Détection automatique des balises `application/ld+json` et des types Schema.org (Article, Product, FAQ, BreadcrumbList, etc.).

### Export CSV

Exportez l'intégralité de votre analyse au format CSV pour l'intégrer dans vos rapports clients.

---

## ❓ FAQ

### L'extension fonctionne-t-elle sur tous les sites ?

L'extension analyse la page affichée dans l'onglet actif. Elle fonctionne sur **toutes les pages web** auxquelles Chrome a accès, y compris les sites en HTTP et HTTPS. Les pages nécessitant une authentification peuvent être analysées si vous êtes connecté dans le navigateur.

### Mes données sont-elles envoyées quelque part ?

En version gratuite, le HTML de la page est envoyé à l'API backend pour analyse. Aucune donnée personnelle ou identifiante n'est conservée. Consultez notre politique de confidentialité pour plus de détails.

### Comment passer à la version Premium ?

Cliquez sur l'icône de couronne 👑 dans l'extension, ou rendez-vous sur notre [page de tarifs](https://votre-site.com/pricing). Le paiement est sécurisé via Stripe (carte bancaire acceptée).

### L'extension est-elle compatible avec les autres Chromium (Edge, Brave, Opera) ?

Oui ! SEO Inspector est une extension Manifest V3 compatible avec tous les navigateurs basés sur Chromium : Google Chrome, Microsoft Edge, Brave, Opera, Vivaldi, etc.

### Puis-je analyser des pages en local ou sur un intranet ?

Oui, à condition que la page soit accessible dans Chrome. L'extension utilise l'API backend pour l'analyse, donc le backend doit pouvoir accéder au contenu HTML (qui est envoyé directement par l'extension, pas fetché côté serveur).

### Comment puis-je contacter le support ?

- **Gratuit** : via le formulaire de contact sur notre site (réponse sous 72h)
- **Premium** : support prioritaire par email, réponse sous 24h ouvrées

---

## 📦 Spécifications techniques

| Spécification | Valeur |
|---|---|
| Version du manifeste | Manifest V3 |
| Permissions | `activeTab`, `storage` |
| Hébergement | Chrome Web Store |
| Analyse backend | API FastAPI (Python 3.11) |
| Score SEO | Algorithme propriétaire pondéré sur 10 critères |

---

## 🔒 Politique de confidentialité

SEO Inspector collecte uniquement le HTML de la page analysée pour produire le rapport SEO. Aucune information personnelle, aucun cookie, aucune donnée de navigation n'est collecté, stocké ou revendu. Les analyses sont anonymes et le HTML est détruit après traitement.
