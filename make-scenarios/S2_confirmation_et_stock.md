# Spécification Technique Make.com - Scénario S2 : Confirmation et Gestion des Stocks

## 1. Vue d'Ensemble
- **Nom du scénario :** `COD-Flow | S2 - Confirmation Client, Verification Stock & Export Transporteur`
- **Déclencheur :** Webhook Telegram (réponse client "OUI", "D'accord", "Confirmer") ou validation interne.
- **Rôle principal :** Valider le devis en commande ferme Odoo 18 (`action_confirm`), réserver le stock (`action_assign`), créer une demande d'achat en cas de rupture de stock, et exporter les détails de la livraison dans la feuille Google Sheet du transporteur COD.

---

## 2. Diagramme Logique du Flux
```
[Webhook Réponse Client "OUI"]
              │
              ▼
[Recherche Devis Odoo (sale.order draft/sent)]
              │
              ▼
[Confirmation Commande (sale.order action_confirm)]
              │
              ▼
[Réservation Stock Picking (action_assign)]
              │
              ├─► [Stock Réservé ?]
              │          │
         NON (Rupture)   │ OUI (Dispo)
              │          │
              │          ├─► [Ajout Ligne Google Sheets Transporteur]
              │          │
              │          ├─► [Mise à jour Odoo x_statut_livraison = 'expedie']
              │          │
              │          └─► [Notification Client "Colis en préparation"]
              ▼
[Création Demande d'Achat Odoo (purchase.order)]
              │
[Alerte Immédiate Rupture au Gérant (Telegram Admin)]
              │
[Notification Client de Réassort 48h]
```

---

## 3. Spécification Détaillée des Modules Make

### Module 1 : Webhook Confirmation Client
- **Type :** `Webhooks > Custom webhook`
- **Filtre de validation :**
  - Le texte entrant correspond aux intentions affirmatives :
    `regexMatch(lower(raw_text); "^(oui|ok|d'accord|confirmer|sifet|marhba|bghitha)$")`
- **Champs reçus :** `sender_id`, `x_message_id`, `raw_text`, `timestamp`.

---

### Module 2 : Recherche du Devis Actif dans Odoo
- **Type :** `HTTP > Make a request` (XML-RPC `/xmlrpc/2/object`)
- **Modèle Odoo :** `sale.order`
- **Méthode :** `search_read`
- **Arguments (args) :**
  ```json
  [
    [
      ["state", "in", ["draft", "sent"]],
      ["partner_id.phone", "=", "{{normalized_phone}}"]
    ]
  ]
  ```
- **Paramètres nommés (kwargs) :**
  ```json
  {
    "fields": ["id", "name", "partner_id", "amount_total", "order_line", "picking_ids"],
    "order": "id desc",
    "limit": 1
  }
  ```
- **Gestion si non trouvé :** Envoi d'un message Telegram : *"Aucun devis en attente trouvé pour votre numéro. Envoyez votre commande pour démarrer."*

---

### Module 3 : Validation de la Commande Odoo (action_confirm)
- **Type :** `HTTP > Make a request` (XML-RPC)
- **Modèle Odoo :** `sale.order`
- **Méthode :** `action_confirm`
- **Arguments (args) :** `[[{{2.id}}]]`
- **Résultat :** La commande passe à l'état `'sale'` et Odoo déclenche la création automatique d'un bon de livraison (`stock.picking`).

---

### Module 4 : Contrôle et Réservation du Bon de Livraison (stock.picking)
- **Étape 4.1 : Lecture du bon de livraison généré**
  - **Modèle Odoo :** `stock.picking`
  - **Méthode :** `search_read`
  - **Arguments (args) :**
    ```json
    [
      [
        ["sale_id", "=", {{2.id}}]
      ]
    ]
    ```
  - **Paramètres nommés (kwargs) :**
    ```json
    {
      "fields": ["id", "name", "state", "move_ids_without_package"]
    }
    ```
- **Étape 4.2 : Tentative d'assignation du stock**
  - **Modèle Odoo :** `stock.picking`
  - **Méthode :** `action_assign`
  - **Arguments :** `[[{{picking_id}}]]`
- **Étape 4.3 : Relecture de l'état du picking**
  - Si `state == 'assigned'` : Tous les articles sont physiquement disponibles et réservés en rayon.
  - Si `state in ['confirmed', 'waiting']` : Au moins un article est en rupture de stock !

---

### Module 5 : Routeur Conditionnel (Disponibilité Stock)

#### Branche A : Stock Réservé avec Succès (`state == 'assigned'`)

1. **Module A.1 : Mise à jour du statut Odoo**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `write`
   - **Arguments :** `[{{2.id}}], {"x_statut_livraison": "expedie"}`

2. **Module A.2 : Export dans Google Sheets Transporteur**
   - **Type :** `Google Sheets > Add a Row`
   - **Spreadsheet ID :** `{{env.GOOGLE_SHEET_ID}}`
   - **Feuille :** `Expeditions_COD`
   - **Mapping des colonnes :**
     - **Date d'expédition :** `{{formatDate(now; "YYYY-MM-DD HH:mm")}}`
     - **N° Commande Odoo :** `{{2.name}}`
     - **Nom Client :** `{{2.partner_id[1]}}`
     - **Téléphone :** `{{normalized_phone}}`
     - **Ville de Destination :** `{{partner_city}}`
     - **Adresse Complète :** `{{partner_street}}`
     - **Montant COD à Encaisser (MAD) :** `{{2.amount_total}}`
     - **Statut Transporteur :** `Prêt pour expédition`
     - **Tentatives de livraison :** `0`
     - **Date Dernier Statut :** `{{formatDate(now; "YYYY-MM-DD")}}`

3. **Module A.3 : Message de Confirmation Expédition au Client**
   - **Type :** `Telegram Bot > Send Text Message`
   - **Contenu :**
     ```text
     ✅ Votre commande {{2.name}} est confirmée !
     
     📦 Notre équipe prépare votre colis pour expédition.
     🚚 Délai de livraison estimé : 24h à 48h ouvrées.
     💵 Montant à régler au livreur : {{2.amount_total}} MAD (en espèces).
     
     Merci de votre confiance !
     ```

---

#### Branche B : Rupture de Stock Détectée (`state != 'assigned'`)

1. **Module B.1 : Création d'une Demande d'Achat Réassort (purchase.order)**
   - **Modèle Odoo :** `purchase.order`
   - **Méthode :** `create`
   - **Arguments :**
     ```json
     {
       "partner_id": 1,
       "origin": "Réassort automatique COD-Flow pour {{2.name}}",
       "order_line": [
         [0, 0, {
           "product_id": {{item.product_id[0]}},
           "product_qty": 20,
           "price_unit": 50.0,
           "date_planned": "{{addDays(now; 2)}}"
         }]
       ]
     }
     ```

2. **Module B.2 : Alerte Prioritaire au Gérant (Telegram Admin)**
   - **Type :** `Telegram Bot > Send Text Message`
   - **Destinataire :** `{{env.TELEGRAM_ADMIN_CHAT_ID}}`
   - **Contenu :**
     ```text
     ⚠️ ALERTE RUPTURE STOCK | COD-Flow
     
     Commande client bloquée : {{2.name}}
     Client : {{2.partner_id[1]}} ({{normalized_phone}})
     Produit en rupture détecté dans l'entrepôt.
     
     Une demande d'achat (PO) a été automatiquement créée dans Odoo pour réapprovisionnement.
     ```

3. **Module B.3 : Message Apaisant au Client**
   - **Contenu :**
     ```text
     Salam ! Votre commande {{2.name}} est bien validée.
     En raison d'un très fort engouement pour ce produit, un délai de préparation supplémentaire de 24h est nécessaire.
     Votre colis partira dès demain. Merci pour votre patience !
     ```

---

## 4. Gestion des Erreurs et Robustesse
- En cas de panne de Google Sheets API : Le module Odoo est déjà validé. Le module utilise une directive `Resume` avec mise en file d'attente (Data Store Make) pour réinjection dès le rétablissement de l'API.

