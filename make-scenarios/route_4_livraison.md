# Route 4 : Livraison, Facturation et Encaissement ("livré S000xx")

## 1. Vue d'Ensemble
- **Objectif :** Dès que le transporteur ou livreur envoie le message `livré S000xx` sur le bot Telegram, valider le bon de livraison dans Odoo 18, générer la facture client, la comptabiliser, enregistrer le paiement en espèces (Cash On Delivery) et notifier le client.
- **Filtre de route Make :** `startsWith(lower(trim(message.text)); "livré")` ou `startsWith(lower(trim(message.text)); "livre")`.
- **Extraction :** Expression régulière pour extraire la référence de commande (ex: `S00012`).

---

## 2. Déroulement Détaillé des Modules

### Module 1 : Recherche du Bon de Livraison (Make an API Call)
- Retrouve le bon de livraison ouvert lié à la référence de commande.
- **Modèle :** `stock.picking`
- **Méthode :** `search_read`
- **Paramètres :**
  - `domain` :
    ```json
    [
      ["origin", "=", "{{sale_order_name}}"],
      ["state", "not in", ["done", "cancel"]]
    ]
    ```
  - `fields` : `["id", "name", "state"]`

### Module 2 : Validation du Bon de Livraison (Make an API Call)
- Valide le bon de livraison pour sortir définitivement les articles du stock physique.
- **Modèle :** `stock.picking`
- **Méthode :** `button_validate`
- **Paramètres :** `[[{{picking_id}}]]`

### Module 3 : Création du Wizard de Facturation (Make an API Call)
- Instancie le wizard standard de facturation d'Odoo pour la commande de vente.
- **Modèle :** `sale.advance.payment.inv`
- **Méthode :** `create`
- **Paramètres :**
  - `args` : `[{"advance_payment_method": "delivered"}]`
  - `kwargs` (contexte actif Odoo) :
    ```json
    {
      "context": {
        "active_model": "sale.order",
        "active_ids": [{{sale_order_id}}]
      }
    }
    ```

### Module 4 : Génération de la Facture Client (Make an API Call)
- Exécute la méthode de création de facture depuis le wizard.
- **Modèle :** `sale.advance.payment.inv`
- **Méthode :** `create_invoices`
- **Paramètres :** `[[{{wizard_id}}]]`

### Module 5 : Recherche de la Facture Générée (Make an API Call)
- Retrouve la facture client créée à l'état brouillon (`draft`).
- **Modèle :** `account.move`
- **Méthode :** `search_read`
- **Paramètres :**
  - `domain` :
    ```json
    [
      ["invoice_origin", "=", "{{sale_order_name}}"],
      ["state", "=", "draft"]
    ]
    ```
  - `fields` : `["id", "name", "amount_total"]`

### Module 6 : Comptabilisation de la Facture (Make an API Call)
- Valide et comptabilise la facture (passe de l'état `draft` à `posted`).
- **Modèle :** `account.move`
- **Méthode :** `action_post`
- **Paramètres :** `[[{{invoice_id}}]]`

### Module 7 : Lecture de la Facture Comptabilisée (Make an API Call)
- Vérifie les montants définitifs et l'état de la pièce comptable.
- **Modèle :** `account.move`
- **Méthode :** `read`
- **Paramètres :**
  - `args` : `[[{{invoice_id}}]]`
  - `kwargs` : `{"fields": ["id", "name", "amount_total", "payment_state"]}`

### Module 8 : Création du Wizard de Paiement COD (Make an API Call)
- Prépare le reçu de paiement en espèces lié à la facture.
- **Modèle :** `account.payment.register`
- **Méthode :** `create`
- **Paramètres :**
  - `args` :
    ```json
    [
      {
        "amount": {{amount_total}},
        "communication": "Paiement COD {{sale_order_name}}"
      }
    ]
    ```
  - `kwargs` (contexte actif Odoo) :
    ```json
    {
      "context": {
        "active_model": "account.move",
        "active_ids": [{{invoice_id}}]
      }
    }
    ```

### Module 9 : Enregistrement Définitif du Paiement (Make an API Call)
- Valide le paiement et applique le lettrage comptable (la facture affiche le bandeau "Payé").
- **Modèle :** `account.payment.register`
- **Méthode :** `action_create_payments`
- **Paramètres :** `[[{{payment_register_id}}]]`

### Module 10 : Notification Client de Clôture
- Envoie un message Telegram au client confirmant la livraison et l'encaissement :
  ```text
  🎉 Votre commande {{sale_order_name}} a bien été livrée !
  Nous confirmons la bonne réception de votre règlement en espèces de {{amount_total}} MAD.
  Toute l'équipe vous remercie pour votre commande et votre confiance !
  ```

