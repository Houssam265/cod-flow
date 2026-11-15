# Cahier des Charges Fonctionnel et Technique - Projet COD-Flow

## 1. Contexte et Objectifs du Projet
Le projet **COD-Flow** est un projet personnel de portfolio en ingénierie logicielle et automatisation ERP (Odoo 18 / Make.com). Il vise à concevoir, déployer et évaluer une architecture d'automatisation des commandes pour les activités de vente en ligne opérant en **Cash On Delivery (COD)**.

### 1.1 Objectifs Clés
- **Automatisation Zéro Saisie :** Éliminer la recopie manuelle des messages de messagerie instantanée dans l'ERP.
- **Fiabilité des Données :** Normaliser l'extraction des données de commande grâce au modèle Gemini (articles, quantités, nom, téléphone, adresse, ville).
- **Cycle Financier et Logistique Intégré :** Valider la livraison, générer la facture client et enregistrer le paiement espèces COD directement dans Odoo dès notification du livreur.

---

## 2. Périmètre Fonctionnel (v1)

### Module F1 : Réception des Messages et Extraction Sémantique
- Capture des messages textuels entrants via un webhook Telegram unique.
- Extraction des entités via Gemini (modèle Flash, gemini-3.6-flash) (offre gratuite) avec le catalogue produit intégré au prompt système :
  - Identité du client (`nom`).
  - Coordonnées téléphoniques (`telephone`).
  - Ville de livraison (`ville`).
  - Adresse de livraison (`adresse`).
  - Articles commandés et quantités (`articles[{code, quantite, prix}]`).

### Module F2 : Intégration ERP Odoo 18 (Module "Make an API Call")
- Déduplication anti-doublon sur une fenêtre de 10 minutes par client.
- Recherche du contact client (`res.partner`, `search_read`) par téléphone.
- Création du contact si absent (`res.partner`, `create`).
- Création du devis de vente (`sale.order`, `create`) avec les lignes d'articles correspondantes et stockage du `chat_id` Telegram dans le champ `client_order_ref` pour la réidentification.
- Envoi du récapitulatif de devis au client avec consigne de répondre `"oui"` pour valider.

### Module F3 : Confirmation et Contrôle de Stock
- Déclenchement sur message `"oui"` du client.
- Recherche du devis en attente (`sale.order`, `search_read`) via la référence de commande (`client_order_ref`).
- Confirmation de la vente (`sale.order`, `action_confirm`), générant le bon de livraison.
- Contrôle de disponibilité physique du stock sur le bon de livraison (`stock.picking`, `search_read`).
- Si rupture de stock (`state != 'assigned'`) : déclenchement d'une alerte Telegram à l'administrateur (ID fixe).

### Module F4 : Clôture Logistique, Facturation et Paiement COD
- Déclenchement sur message transporteur `"livré S000xx"`.
- Recherche et validation du bon de livraison (`stock.picking`, `button_validate`).
- Création de la facture client via le wizard Odoo (`sale.advance.payment.inv`, `create` puis `create_invoices`).
- Recherche et comptabilisation de la facture (`account.move`, `search_read`, `action_post`, `read`).
- Enregistrement du paiement espèces COD (`account.payment.register`, `create` puis `action_create_payments`).
- Notification Telegram de confirmation de livraison et d'encaissement envoyée au client.

---

## 3. Spécifications Techniques et Contraintes

### 3.1 Environnement et Stack Logicielle
- **ERP :** Odoo 18.0 Community Edition conteneurisé sous Docker.
- **Base de Données :** PostgreSQL 16 Alpine conteneurisé avec volumes persistants.
- **Port Odoo :** Port configurable (`${ODOO_PORT:-8269}` en local par défaut).
- **Exposition Réseau :** Service ngrok conteneurisé exposant Odoo via un domaine fixe HTTPS pour les webhooks Make.
- **Orchestration :** Scénario unique Make.com avec routeur (dû à la contrainte d'un webhook unique par bot Telegram). Tous les appels Odoo utilisent le module natif "Make an API Call".
- **IA :** Gemini (modèle Flash, gemini-3.6-flash) (offre gratuite avec prompt incluant le catalogue).
- **Scripts d'Initialisation :** Python 3 (bibliothèque standard) pour l'idempotence des configurations.

### 3.2 Sécurité et Données
- **Gestion des Secrets :** Aucun secret versionné ; utilisation exclusive du fichier `.env` protégé par `.gitignore`.
- **Données Personnelles :** Données de test uniquement. Utilisation de coordonnées fictives pour les démonstrations.

---

## 4. Limites de la v1
1. **Confirmation restreinte :** Validation client déclenchée uniquement par le mot exact `"oui"`.
2. **Fenêtre anti-doublon :** Détection limitée à une fenêtre de 10 minutes par client.
3. **Catalogue statique dans le prompt :** Le catalogue produit est inscrit directement dans le prompt système Gemini.
4. **Référence de commande :** L'identifiant de chat Telegram est stocké dans le champ `client_order_ref` du devis `sale.order`.
5. **Administrateur unique :** L'identifiant Telegram administrateur pour les alertes de rupture est fixe.
6. **Disponibilité locale :** Le PC hôte, Docker et le conteneur ngrok doivent rester allumés pour maintenir la passerelle active.
7. **Offre gratuite Gemini :** Utilisation de l'API gratuite Gemini (les données peuvent être traitées pour améliorer les produits Google : données de test uniquement).
8. **Périmètre logistique restreint :** Pas de feuille transporteur Google Sheets, pas de rapport quotidien automatisé, pas de relances J+1/J+2 et pas de gestion des livraisons refusées.
9. **Conditions expérimentales :** Échantillon de test de 5 commandes, un seul opérateur, temps manuel dépendant de la concentration.

---

## 5. Évolutions (v2)
- **Canaux e-commerce :** Intégration de connecteurs pour boutiques en ligne WooCommerce et Shopify.
- **Supervision avancée :** Génération et diffusion d'un rapport quotidien d'activité à heure fixe.
- **Relances automatisées :** Protocole de relance à J+1 et J+2 pour les destinataires injoignables.
- **Réapprovisionnement :** Génération automatique d'une demande de prix fournisseur (`purchase.order`) en cas de rupture.
- **Canal WhatsApp :** Extension du bot conversationnel sur WhatsApp Business API.
