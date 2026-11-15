# Protocole de Mesure et Grille Comparative : Saisie Manuelle vs COD-Flow

## 1. Contexte et Objectif Expérimental
Le Cash On Delivery (COD) au Maroc souffre traditionnellement d'une forte friction opérationnelle :
- Les clients envoient des messages informels en Darija ou en Français sur WhatsApp ou Telegram.
- Le commerçant doit déchiffrer chaque message, basculer sur son ERP (Odoo), créer manuellement la fiche client, sélectionner les articles, vérifier le stock et créer le devis/bon de livraison.
- Ce processus manuel est chronophage, source d'erreurs (fautes sur le numéro de téléphone, erreurs de références) et incapable de détecter efficacement les commandes passées en double par inadvertance.

**Objectif du test :**
Mesurer quantitativement l'impact de **COD-Flow** sur un échantillon de **5 commandes complètes** (1 en français, 1 en darija, 1 avec fautes d'orthographe, 1 au format +212 avec espaces, 1 sans quantité spécifiée) ainsi qu'un **message incomplet**, en comparant :
1. **Méthode A (Manuelle)** : Saisie directe par un opérateur dans l'interface Odoo 18.
2. **Méthode B (COD-Flow)** : Traitement entièrement automatisé (Make.com + Gemini + Odoo 18).

---

## 2. Protocole Opératoire

### Méthode A : Saisie Manuelle dans Odoo
- **Prérequis :** Interface Odoo 18 ouverte sur le module *Ventes*, environnement local.
- **Déroulement pour chaque commande :**
  1. Démarrer le chronomètre dès l'ouverture du message client.
  2. Lire et interpréter le texte (articles, quantités, nom, téléphone et adresse).
  3. Dans Odoo, cliquer sur **Créer un devis**.
  4. Créer ou associer le client (`res.partner`) avec son téléphone, sa ville et son adresse.
  5. Ajouter les lignes de commande correspondantes aux articles.
  6. Sauvegarder le devis.
  7. Consigner le temps total chronométré et les erreurs observées.

### Méthode B : Automatisation COD-Flow
- **Prérequis :** Conteneurs Odoo 18 et ngrok actifs, scénario Make (Route 1) opérationnel.
- **Déroulement :**
  1. Envoi des messages de test sur le bot Telegram.
  2. Traitement automatique : extraction sémantique via Gemini, contrôle anti-doublon (10 min), création contact et devis Odoo.
  3. Pour le message incomplet : vérification que le bot formule la relance pour obtenir les éléments manquants.
  4. Consignation des durées réelles d'exécution et du statut de conformité.

---

## 3. Synthèse des Résultats Réels Mesurés

Mesures réelles obtenues par un opérateur unique en conditions locales :

| Indicateur Clé de Performance (KPI) | Saisie Manuelle (A) | COD-Flow Automatisé (B) | Écart / Réduction |
| :--- | :--- | :--- | :--- |
| **Temps total (5 commandes)** | ~420 s | ~45 s | Réduction d'environ 89 % |
| **Temps moyen par commande** | ~84 s | ~9 s | Réduction d'environ 89 % |
| **Nombre d'erreurs de saisie** | 1 / 5 (erreur sur l'adresse) | 0 / 5 | -100 % d'erreurs |
| **Message incomplet envoyé** | Saisie bloquée / appel nécessaire | Bot a demandé les informations manquantes | Traitement conforme |

---

## 4. Analyse des Écarts Constatés
1. **Erreur d'adresse en saisie manuelle :** Sur les 5 commandes manuelles, 1 erreur de recopie d'adresse est survenue sous l'effet de la fatigue visuelle.
2. **Gestion des dialectes et fautes :** COD-Flow (Gemini) a correctement restitué les commandes en Darija translittérée, avec fautes ou sans quantité explicite (quantité implicite de 1 appliquée avec exactitude).
3. **Cas du message incomplet :** Le bot n'a pas créé de commande invalide et a correctement demandé au client les coordonnées manquantes.

---

## 5. Limites
Ce protocole expérimental présente les limites méthodologiques suivantes :
- **Échantillon de 5 commandes :** Le test a été conduit sur un échantillon restreint de 5 commandes complètes et 1 message incomplet, permettant de valider les fonctionnalités nominales et limites sans constituer une étude statistique à grand volume.
- **Un seul opérateur :** Les mesures manuelles ont été réalisées par un unique opérateur.
- **Dépendance à la concentration :** Le temps de traitement manuel est fortement dépendant du niveau de concentration et de la rapidité de l'opérateur au moment du test.
- **Conditions de test locales :** Tests réalisés dans un environnement local (Docker et tunnel ngrok), sans intégrer la latence réseau d'une infrastructure de production distribuée.

