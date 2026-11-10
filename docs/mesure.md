# Protocole de Mesure et Grille Comparative : Saisie Manuelle vs COD-Flow

## 1. Contexte et Objectif Expérimental
Le Cash On Delivery (COD) au Maroc souffre traditionnellement d'une forte friction opérationnelle :
- Les clients envoient des messages informels en Darija ou en Français sur WhatsApp ou Telegram.
- Le commerçant doit déchiffrer chaque message, basculer sur son ERP (Odoo), créer manuellement la fiche client, sélectionner les articles, vérifier le stock et créer le devis/bon de livraison.
- Ce processus manuel est chronophage, source d'erreurs (fautes sur le numéro de téléphone, erreurs de références) et incapable de détecter efficacement les commandes passées en double par inadvertance.

**Objectif du test :**
Mesurer quantitativement l'impact de **COD-Flow** sur un échantillon standardisé de **20 commandes représentatives** (issues de `llm/messages_test.json`), en comparant :
1. **Méthode A (Manuelle)** : Saisie directe par un opérateur humain dans l'interface Odoo 18.
2. **Méthode B (COD-Flow)** : Traitement entièrement automatisé (LLM + Make.com + XML-RPC Odoo 18).

---

## 2. Protocole Opératoire

### Méthode A : Saisie Manuelle dans Odoo
- **Prérequis :** Interface Odoo 18 ouverte sur le module *Ventes*.
- **Déroulement pour chaque commande :**
  1. Démarrer le chronomètre dès l'ouverture du message client.
  2. Lire et interpréter le texte (identifier les articles, quantités, nom, téléphone et adresse).
  3. Dans Odoo, cliquer sur **Créer un devis**.
  4. Créer ou associer le client (`res.partner`) avec son téléphone, sa ville et son adresse.
  5. Ajouter manuellement les lignes de commande correspondantes aux articles.
  6. Sauvegarder le devis.
  7. Arrêter le chronomètre et consigner :
     - Le temps écoulé (en secondes).
     - Le statut de conformité (Conforme / Erreur).
     - La nature de l'erreur le cas échéant (ex: mauvais numéro, oubli d'un article, faute sur le nom).
     - La détection ou non d'un doublon (notamment sur MSG-15).

### Méthode B : Automatisation COD-Flow
- **Prérequis :** Conteneur Odoo 18 actif, scénario Make S1 en écoute.
- **Déroulement :**
  1. Lancer le script simulateur :
     ```bash
     python tests/send_test_messages.py --count 20 --delay 2
     ```
  2. Le script enregistre automatiquement dans `tests/logs/` la durée d'exécution totale de chaque requête en millisecondes.
  3. Vérifier dans Odoo 18 la commande créée :
     - Conformité de l'extraction LLM.
     - Normalisation du téléphone au format `+212`.
     - Blocage automatique du doublon (message MSG-15).
     - Gestion des messages incomplets avec demande d'information.
  4. Reporter les temps et résultats réels dans `docs/mesure.csv`.

---

## 3. Grille de Synthèse des Métriques à Renseigner

> **Note d'intégrité :** Les cellules ci-dessous doivent être complétées avec vos mesures chronométrées réelles. Aucun chiffre fictif n'a été inséré.

| Indicateur Clé de Performance (KPI) | Saisie Manuelle (A) | COD-Flow Automatisé (B) | Écart / Gain |
| :--- | :--- | :--- | :--- |
| **Temps moyen par commande** | [X] s | [Y] s | - [Z] % |
| **Temps total pour 20 commandes** | [X] min [Y] s | [X] min [Y] s | - [Z] % |
| **Nombre d'erreurs de saisie** | [X] / 20 | [Y] / 20 | - [Z] % |
| **Taux de conformité des données** | [X] % | [Y] % | + [Z] % |
| **Détection du doublon (MSG-15)** | [Détecté / Non détecté] | [Détecté / Non détecté] | N/A |
| **Détection rupture stock (MSG-05)** | [Vérifié / Non vérifié] | [Automatisé / Alerte] | N/A |

---

## 4. Analyse Qualitative des Erreurs Fréquentes
Lors de vos essais manuels, classez les erreurs observées dans les catégories suivantes :
1. **Erreur d'inattention sur le numéro :** Numéro à 9 chiffres au lieu de 10, inversion de chiffres, oubli de l'indicatif.
2. **Ambiguïté Darija non résolue :** Confusion sur les unités (ex: "jouj" pris pour 1, confusion entre Sérum et Huile).
3. **Doublon non détecté :** Création d'une seconde commande identique pour le même client à quelques minutes d'intervalle.
4. **Omission d'adresse :** Validation d'un bon de commande alors qu'il manque le quartier ou la rue, bloquant la livraison finale.

---

## 5. Limites
Ce protocole expérimental présente plusieurs limites méthodologiques à prendre en compte lors de l'interprétation des résultats :
- **Un seul opérateur :** L'évaluation manuelle est exécutée par un opérateur unique, ce qui n'intègre pas la variabilité de cadence ou d'expérience entre différents utilisateurs.
- **Échantillon de 20 messages :** Le jeu de données se limite à un panel représentatif de 20 cas de test, suffisant pour valider les comportements nominaux et limites, mais ne constituant pas un échantillon statistique à grande échelle.
- **Conditions de test locales :** Les mesures sont réalisées dans un environnement de test local (conteneur Docker et scripts locaux), sans les latences réseau variables, les temps d'attente de webhooks distants ou la charge concurrente d'une exploitation en production.

