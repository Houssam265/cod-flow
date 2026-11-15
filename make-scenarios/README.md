# Spécification Make.com - Scénario Unique avec Routeur

## 1. Architecture du Scénario Unique

Dans COD-Flow v1, l'ensemble des flux est orchestré au sein d'**un seul scénario Make.com**, pour une raison technique fondamentale liée à Telegram :
- **Contrainte Telegram :** L'API Telegram Bot n'autorise qu'**un seul webhook actif par bot** (`setWebhook`). Il est impossible d'enregistrer plusieurs webhooks distincts pour un même bot.
- **Solution :** Tous les messages entrants transitent par un **Webhook Telegram unique**, qui alimente un **Routeur Make.com** chargé d'aiguiller le traitement vers 4 routes spécialisées selon le contenu du message.

---

## 2. Interaction avec Odoo via "Make an API Call"

Toutes les interactions avec Odoo 18 s'effectuent au moyen du module natif Odoo **"Make an API Call"** dans Make.com :
- **Connexion :** Via le tunnel ngrok exposé (`https://${NGROK_DOMAIN}`).
- **Structure d'appel :** Chaque module renseigne le **Modèle** Odoo (`model`), la **Méthode** ORM (`method`) et les **Paramètres** (`args` et `kwargs`).

---

## 3. Synthèse des 4 Routes du Routeur

| Route | Fiche technique | Déclencheur / Filtre | Actions principales | Modèles Odoo sollicités |
| :--- | :--- | :--- | :--- | :--- |
| **Route 1** | [route_1_nouvelle_commande.md](route_1_nouvelle_commande.md) | Message texte libre (commande) | Extraction Gemini (catalogue dans le prompt), anti-doublon 10 min, création client, création devis (`client_order_ref` = chat_id), récapitulatif client | `res.partner` (search_read, create)<br/>`sale.order` (create) |
| **Route 2** | [route_2_confirmation.md](route_2_confirmation.md) | Message exact `"oui"` | Recherche devis en cours, confirmation de vente, vérification disponibilité stock | `sale.order` (search_read, action_confirm)<br/>`stock.picking` (search_read) |
| **Route 3** | [route_3_rupture_stock.md](route_3_rupture_stock.md) | Stock non réservé (`state != 'assigned'`) | Alerte rupture sur Telegram Admin (ID fixe), notification de délai au client | Aucun (orchestration Telegram) |
| **Route 4** | [route_4_livraison.md](route_4_livraison.md) | Message `"livré S000xx"` | Validation livraison, création facture via wizard, comptabilisation, enregistrement paiement espèces COD | `stock.picking` (search_read, button_validate)<br/>`sale.advance.payment.inv` (create, create_invoices)<br/>`account.move` (search_read, action_post, read)<br/>`account.payment.register` (create, action_create_payments) |

