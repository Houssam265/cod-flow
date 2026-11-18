# COD-Flow : Automatisation ERP Odoo 18 pour le Cash On Delivery (Maroc)

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0%20Community-purple.svg)](https://www.odoo.com/)
[![Docker](https://img.shields.io/badge/Docker-Postgres%2016-blue.svg)](https://www.docker.com/)
[![Make.com](https://img.shields.io/badge/Orchestration-Make.com-purple.svg)](https://www.make.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B%20Stdlib-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

---

## 📌 Présentation du Projet
Une commande reçue par message doit être ressaisie à la main dans l'ERP : lire le texte informel (Français, Darija, fautes de frappe), créer ou retrouver le contact, ajouter les lignes d'articles et enregistrer le devis — avant même de vérifier le stock ou d'envoyer une confirmation. Dans un contexte **Cash On Delivery (COD)** où les volumes peuvent être importants, ce traitement manuel répété est une source majeure de lenteur et d'erreurs.

La gestion manuelle de ce flux impose des contraintes opérationnelles :
- **Temps de saisie manuel significatif :** Traitement de chaque message informel pour créer le contact client dans l'ERP, sélectionner les articles et générer le devis (durée à mesurer).
- **Risques d'erreurs :** Coordonnées téléphoniques erronées ou adresses incomplètes pouvant bloquer la livraison.
- **Gestion des doublons et ruptures :** Risque de doublons lors de commandes répétées et nécessité de détecter immédiatement les ruptures de stock à la confirmation.
- **Clôture comptable à la livraison :** Nécessité d'enregistrer la facture et le paiement en espèces dès remise du colis par le transporteur.

**COD-Flow** est un **projet personnel de portfolio en automatisation ERP** reliant un bot Telegram, l'API Google Gemini, un scénario Make.com unique à 4 routes, et **Odoo 18 Community** exposé via un tunnel ngrok :
```text
Message Telegram (Client / Livreur)
  ──► Webhook Unique Make.com
  ──► Routeur Make (4 routes)
        ├── Route 1 : Nouvelle commande (Gemini (modèle Flash, gemini-3.6-flash) ──► Odoo res.partner + sale.order)
        ├── Route 2 : Confirmation "oui" (Odoo sale.order action_confirm + contrôle stock)
        ├── Route 3 : Rupture de stock (Alerte Telegram Admin)
        └── Route 4 : Livraison "livré S000xx" (Odoo picking + facture + paiement COD)
```

---

## 🏛️ Architecture Globale

Consultez la [documentation d'architecture détaillée](docs/architecture.md) pour les spécifications complètes.

```mermaid
flowchart TD
    subgraph Client["Canal Telegram"]
        TG["Telegram Bot<br/>(Webhook Unique)"]
    end

    subgraph Make["Scénario Unique Make.com"]
        WH["Webhook Telegram"]
        ROUTER{"Routeur Make<br/>(Aiguillage)"}
        
        R1["Route 1 : Nouvelle Commande<br/>(Gemini + Client + Devis)"]
        R2["Route 2 : Confirmation<br/>('oui' -> action_confirm)"]
        R3["Route 3 : Rupture de Stock<br/>(Alerte Admin)"]
        R4["Route 4 : Livraison & Clôture<br/>('livré S000xx' -> Picking + Facture + Paiement)"]
    end

    subgraph IA["Intelligence Artificielle"]
        GEMINI["Gemini (modèle Flash, gemini-3.6-flash)<br/>(Catalogue dans le prompt)"]
    end

    subgraph Tunnel["Tunnel ngrok"]
        NGROK["https://${NGROK_DOMAIN}"]
    end

    subgraph ERP["ERP Odoo 18 Community (Docker)"]
        PARTNER["res.partner<br/>(search_read / create)"]
        SO["sale.order<br/>(create / action_confirm)"]
        PICK["stock.picking<br/>(search_read / button_validate)"]
        WIZ_INV["sale.advance.payment.inv<br/>(create / create_invoices)"]
        INV["account.move<br/>(search_read / action_post / read)"]
        PAY["account.payment.register<br/>(create / action_create_payments)"]
    end

    subgraph Admin["Supervision"]
        ADMIN_TG["Telegram Admin<br/>(ID fixe)"]
    end

    TG -->|Message entrant| WH
    WH --> ROUTER

    ROUTER -->|"Message commande"| R1
    R1 -->|Extraction entités| GEMINI
    GEMINI -->|JSON extrait| R1
    R1 -->|"Make an API Call"| NGROK
    NGROK --> PARTNER
    NGROK --> SO
    R1 -.->|Récapitulatif devis| TG

    ROUTER -->|"Message 'oui'"| R2
    R2 -->|"Make an API Call"| NGROK
    NGROK --> SO
    NGROK --> PICK
    R2 -.->|"Confirmation préparation"| TG

    R2 -.->|"Stock non réservé"| R3
    R3 -->|Alerte rupture| ADMIN_TG
    R3 -.->|Notification délai| TG

    ROUTER -->|"Message 'livré S000xx'"| R4
    R4 -->|"Make an API Call"| NGROK
    NGROK --> PICK
    NGROK --> WIZ_INV
    NGROK --> INV
    NGROK --> PAY
    R4 -.->|Confirmation encaissement| TG
```

> **Pourquoi un seul scénario Make ?** L'API Telegram Bot n'autorise qu'**un seul webhook actif par bot**. Toutes les interactions transitent donc par un webhook unique et sont aiguillées par un routeur Make. Tous les appels vers Odoo utilisent le module natif **"Make an API Call"** via le tunnel ngrok.

<p align="center">
  <img src="docs/images/01-scenario-make.png" alt="Scénario Unique Make.com avec Routeur" width="100%"/>
  <br/>
  <em>Figure 1 : Vue globale du scénario unique Make.com orchestrant les 4 routes via l'API Telegram et le module natif « Make an API Call » Odoo 18.</em>
</p>

---

## 📸 Démonstration Visuelle du Cycle COD-Flow

Le cycle complet de vente Cash On Delivery (de la réception du message informel à la clôture comptable) est illustré ci-dessous à partir de captures réelles du projet :

### 1. Route 1 : Prise de Commande Conversationnelle & Création du Devis
Le client formule sa commande en langage naturel (français ou darija). Gemini (modèle Flash) extrait les coordonnées et le panier, puis Odoo 18 crée le contact et génère le devis chiffré :

| Échange Telegram (Client / Bot) | Devis généré dans Odoo 18 Community |
| :---: | :---: |
| <img src="docs/images/02-telegram-commande.png" alt="Message Telegram de commande" width="340"/> | <img src="docs/images/03-odoo-devis.png" alt="Devis créé dans Odoo 18" width="580"/> |
| *Réception du message informel et envoi immédiat du devis.* | *Devis créé avec articles et référence client.* |

---

### 2. Route 2 : Confirmation Client & Réservation du Stock
Dès que le client répond le mot `« oui »`, le devis est validé en commande de vente ferme (`action_confirm`). Le bon de livraison (`stock.picking`) est automatiquement créé et le stock physique est réservé :

| Réponse client « oui » sur Telegram | Bon de livraison Odoo 18 à l'état « Prêt » |
| :---: | :---: |
| <img src="docs/images/04-telegram-confirmation.png" alt="Confirmation Telegram oui" width="460"/> | <img src="docs/images/05-odoo-livraison-prete.png" alt="Bon de livraison Odoo 18 prêt" width="580"/> |
| *Validation instantanée de la commande par le client.* | *Bon de livraison avec articles réservés (« Disponible »).* |

---

### 3. Route 3 : Détection et Alerte de Rupture de Stock
Si la quantité demandée excède le stock disponible, le bon de livraison passe à l'état « En attente ». Le routeur Make alerte immédiatement l'administrateur et informe le client :

| Alertes Telegram (Client & Admin) | Bon de livraison Odoo 18 en attente |
| :---: | :---: |
| <img src="docs/images/06-rupture.png" alt="Alerte rupture Telegram" width="340"/> | <img src="docs/images/06b-odoo-bon-en-attente.png" alt="Bon de livraison en attente" width="580"/> |
| *Notification client de réapprovisionnement & alerte admin.* | *Bon de livraison marqué « Pas disponible » (rupture).* |

---

### 4. Route 4 : Validation de Livraison, Facturation & Encaissement COD
Dès notification par le livreur (`« livré S000xx »`), Odoo valide la livraison physique (`button_validate`), génère la facture client via wizard, la comptabilise (`action_post`) et enregistre le règlement en espèces :

| Signalement du livreur sur Telegram | Facture Odoo 18 comptabilisée et payée |
| :---: | :---: |
| <img src="docs/images/07-telegram-livraison.png" alt="Livraison Telegram validée" width="340"/> | <img src="docs/images/08-facture-payee.png" alt="Facture Odoo 18 Payée" width="580"/> |
| *Confirmation du livreur et notification client d'encaissement.* | *Facture comptabilisée avec ruban vert « PAYÉ ».* |

---

## 📁 Arborescence du Dépôt

```text
COD-Flow/
├── LICENSE                      # Licence MIT (HARISS Houssam)
├── README.md                    # Documentation principale du projet
├── odoo/
│   ├── docker-compose.yml       # Odoo 18 + PostgreSQL 16 + service ngrok (port configurable)
│   ├── .env.example             # Modèle de variables d'environnement (valeurs factices)
│   ├── .gitignore               # Protection des données locales et secrets
│   ├── odoo_client.py           # Client XML-RPC avec gestion d'erreurs et normalisation de domaines
│   ├── test_odoo_api.py         # Test de connexion et vérification des modules
│   ├── create_custom_fields.py  # Création idempotente des champs x_* sur sale.order
│   ├── seed_products.py         # Produits démo et stock initial via stock.quant
│   ├── seed_customers.py        # 5 clients démo avec numéros normalisés (+212)
│   ├── seed_orderpoints.py      # Règles de stock minimum par produit
│   └── check_setup.py           # Contrôle de conformité global (vérification stricte des stocks)
├── make-scenarios/
│   ├── README.md                # Vue d'ensemble du scénario unique et contrainte webhook
│   ├── route_1_nouvelle_commande.md  # Route 1 : Commande, Gemini, res.partner, sale.order
│   ├── route_2_confirmation.md       # Route 2 : Confirmation "oui", action_confirm, stock
│   ├── route_3_rupture_stock.md      # Route 3 : Alerte rupture admin Telegram
│   └── route_4_livraison.md          # Route 4 : Livré S000xx, picking, facture, paiement
├── llm/
│   ├── prompt_extraction.md     # Prompt système d'extraction (Français / Darija)
│   ├── schema.json              # Schéma JSON strict (Structured Outputs)
│   └── messages_test.json       # 22 messages de test variés
├── tests/
│   └── send_test_messages.py    # Script de test (non utilisé dans la démo finale)
└── docs/
    ├── images/                  # Captures d'écran (Make, Telegram, Odoo 18, Résultats)
    │   ├── 01-scenario-make.png
    │   ├── 02-telegram-commande.png
    │   ├── 03-odoo-devis.png
    │   ├── 04-telegram-confirmation.png
    │   ├── 05-odoo-livraison-prete.png
    │   ├── 06-rupture.png
    │   ├── 06b-odoo-bon-en-attente.png
    │   ├── 07-telegram-livraison.png
    │   ├── 08-facture-payee.png
    │   └── 09-resultats.png
    ├── architecture.md          # Architecture technique et schéma Mermaid
    ├── cahier_des_charges.md    # Cahier des charges fonctionnel et technique
    ├── mesure.md                # Protocole expérimental et résultats réels
    └── mesure.csv               # Grille tabulaire des mesures
```

---

## 🛠️ Prérequis Système
- **Docker Desktop** ou moteur Docker avec Docker Compose.
- **Python 3.10+** (bibliothèque standard uniquement, sans dépendances tierces).
- Compte gratuit **Make.com** (scénario unique avec routeur).
- Compte **Telegram** (création d'un bot via `@BotFather` et identifiant administrateur).
- Compte **Google AI Studio** (clé API gratuite pour Gemini (modèle Flash, gemini-3.6-flash)).
- Compte gratuit **ngrok** avec domaine fixe configuré.

---

## 🚀 Guide d'Installation Pas à Pas

### 1. Préparer l'environnement
```bash
git clone https://github.com/Houssam265/cod-flow.git
cd cod-flow

# Créer votre fichier d'environnement à partir du modèle
cp odoo/.env.example odoo/.env
# Sous Windows PowerShell : Copy-Item odoo/.env.example odoo/.env
```

Éditez le fichier `odoo/.env` avec vos identifiants réels (mots de passe, tokens Telegram, clé Gemini, tokens ngrok).

---

### 2. Démarrer Odoo 18 et ngrok avec Docker
Le port Odoo exposé sur la machine hôte est configurable via la variable `ODOO_PORT` (par défaut `8269`).
```bash
cd odoo
docker compose up -d
```
Les trois conteneurs démarrent :
1. `codflow_postgres16` : Base de données PostgreSQL 16.
2. `codflow_odoo18` : Serveur Odoo 18 Community accessible sur `http://localhost:8269`.
3. `codflow_ngrok` : Tunnel HTTPS exposant le port Odoo sur votre domaine fixe (`https://${NGROK_DOMAIN}`).

Accédez à `http://localhost:8269` (ou votre port configuré) :
1. Créez une nouvelle base de données (ex: `codflow_db`) avec l'utilisateur administrateur (ex: `admin@codflow.ma`).
2. Dans le menu **Applications (Apps)** d'Odoo, installez les trois modules indispensables :
   - **Ventes** (`sale_management`)
   - **Inventaire** (`stock`)
   - **Facturation** (`account`)
3. Chargez le plan comptable marocain : **Facturation → Configuration → Paramètres → Localisation fiscale** → sélectionner la localisation Maroc et appliquer.

---

### 3. Exécuter les scripts de configuration automatique
Les scripts Python sont idempotents et s'exécutent dans l'ordre :
```bash
cd odoo

# 1. Tester la communication XML-RPC avec Odoo
python test_odoo_api.py

# 2. Créer les champs personnalisés sur sale.order
python create_custom_fields.py

# 3. Créer les articles du catalogue et initialiser les stocks (50, 80, 30, 25, 5)
python seed_products.py

# 4. Créer les 5 clients de démo avec numéros normalisés (+212)
python seed_customers.py

# 5. Configurer les règles de stock minimum (Orderpoints)
python seed_orderpoints.py

# 6. Vérifier la conformité globale (contrôle strict des stocks attendus)
python check_setup.py
```

Le script `check_setup.py` doit valider la configuration avec un rapport global **100% [SUCCÈS]**.

---

### 4. Importer le Blueprint Make.com
Importez le fichier `make-scenarios/cod-flow.blueprint.json` directement dans Make.com :
1. Dans Make.com, cliquez sur **Créer un nouveau scénario** → **Importer un Blueprint**.
2. Sélectionnez le fichier `make-scenarios/cod-flow.blueprint.json`.
3. Reconnectez les connexions (Telegram Bot, Google AI — Gemini, Odoo) sur chaque module.
4. Configurez le webhook Telegram (`setWebhook`) avec l'URL ngrok affichée dans les logs du conteneur `codflow_ngrok`.
5. Activez le scénario.

---

### 5. Configuration du Scénario Make.com (documentation détaillée)
Consultez les fiches de spécification rédigées dans `make-scenarios/` :
1. Configurez le webhook unique Telegram : [README make-scenarios](make-scenarios/README.md).
2. Configurez la [Route 1 : Nouvelle Commande](make-scenarios/route_1_nouvelle_commande.md).
3. Configurez la [Route 2 : Confirmation "oui"](make-scenarios/route_2_confirmation.md).
4. Configurez la [Route 3 : Rupture de Stock](make-scenarios/route_3_rupture_stock.md).
5. Configurez la [Route 4 : Livraison, Facturation & Paiement](make-scenarios/route_4_livraison.md).

---

## ⚠️ Limites de la v1
1. **Confirmation par le seul mot « oui » :** La confirmation client n'est traitée que si le message reçu est `"oui"` (insensible à la casse — `"OUI"`, `"Oui"` sont acceptés).
2. **Anti-doublon limité :** La fenêtre de détection des doublons est fixée à 10 minutes par client ; le verrou interne (`x_message_id`) n'a pas été testé en conditions réelles de charge simultanée.
3. **Catalogue produit dans le prompt :** Les références et prix des 5 produits sont inscrits directement dans le prompt système Gemini.
4. **Identifiant de chat dans la référence de commande :** Le `chat_id` Telegram est conservé dans le champ `client_order_ref` de `sale.order`.
5. **Extraction du numéro de commande :** La Route 4 suppose un numéro au format `S0XXXX` (6 caractères, ex: `S00031`) — un format différent ne serait pas reconnu.
6. **Identifiant administrateur fixe :** L'alerte de rupture est transmise à un ID Telegram statique.
7. **Infrastructure dépendante du poste local :** L'ordinateur, Docker et le tunnel ngrok doivent demeurer allumés pour traiter les flux.
8. **Offre gratuite Gemini :** Utilisation du niveau gratuit de l'API Gemini (les données peuvent servir à améliorer les produits Google : **données de test uniquement**, aucune donnée personnelle réelle).
9. **Périmètre simplifié :** Pas de feuille Google Sheets transporteur, pas de rapport quotidien à heure fixe, pas de relances automatiques J+1/J+2 et pas de gestion des colis refusés.
10. **Conditions expérimentales :** Échantillon de test de 5 commandes, un seul opérateur, temps manuel dépendant de la concentration.

---

## 🔮 Évolutions (v2)
- **Canal e-commerce :** Connecteurs directs pour boutiques WooCommerce et Shopify.
- **Rapport quotidien :** Synthèse quotidienne automatisée des commandes et encaissements à 18h.
- **Relances clients :** Gestion programmée des relances à J+1 et J+2 pour les destinataires injoignables.
- **Demande d'achat automatique :** Création automatique d'un bon de commande fournisseur (`purchase.order`) en cas de rupture de stock.
- **Canal WhatsApp :** Prise en charge de WhatsApp Business API.

---

## 📊 Résultats Expérimentaux (Données Réelles)

Mesures réelles réalisées sur un échantillon de 5 commandes complètes (1 en français, 1 en darija, 1 avec fautes, 1 au format +212 avec espaces, 1 sans quantité) par un opérateur, en local :

<p align="center">
  <img src="docs/images/09-resultats.png" alt="Tableau comparatif des résultats réels - Saisie manuelle vs COD-Flow" width="100%"/>
  <br/>
  <em>Figure 2 : Synthèse comparative sous tableur des mesures de performance et de fiabilité (Saisie manuelle vs COD-Flow).</em>
</p>

| Indicateur de Performance | Saisie Manuelle dans Odoo | COD-Flow Automatisé | Gain / Écart |
| :--- | :--- | :--- | :--- |
| **Temps total (5 commandes)** | ~420 s (environ 7 min) | ~45 s | Réduction d'environ 89 % |
| **Temps moyen par commande** | ~84 s | ~9 s | Réduction d'environ 89 % |
| **Erreurs de saisie** | 1 / 5 (adresse) | 0 / 5 | 0 erreur sur 5 |
| **Message incomplet** | non mesuré | Bot a demandé les infos manquantes | Conforme |

---

## 📜 Licence et Auteur
Projet personnel de portfolio en ingénierie logicielle et automatisation ERP réalisé par **HARISS Houssam**.  
Distribué sous licence **MIT** (voir fichier [LICENSE](LICENSE)).
