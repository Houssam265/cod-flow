# Route 2 : Confirmation de Commande ("oui")

## 1. Vue d'Ensemble
- **Objectif :** Valider le devis en commande de vente ferme dans Odoo 18 dès que le client répond le mot `"oui"`, puis contrôler la disponibilité du stock physique dans l'entrepôt.
- **Filtre de route Make :** `lower(trim(message.text)) == "oui"`.

---

## 2. Déroulement Détaillé des Modules

### Module 1 : Recherche du Devis en Attente (Make an API Call)
- Retrouve le devis le plus récent au statut brouillon ou envoyé (`draft` ou `sent`) associé au client (grâce au `chat_id` présent dans le champ `client_order_ref` de `sale.order`).
- **Modèle :** `sale.order`
- **Méthode :** `search_read`
- **Paramètres :**
  - `domain` :
    ```json
    [
      ["state", "in", ["draft", "sent"]],
      ["client_order_ref", "=", "{{telegram_chat_id}}"]
    ]
    ```
  - `fields` : `["id", "name", "partner_id", "amount_total"]`
  - `order` : `"id desc"`
  - `limit` : `1`

### Module 2 : Confirmation de la Vente Odoo (Make an API Call)
- Déclenche la transition du devis vers l'état commande confirmée (`sale`), ce qui génère automatiquement le bon de livraison (`stock.picking`).
- **Modèle :** `sale.order`
- **Méthode :** `action_confirm`
- **Paramètres :** `[[{{sale_order_id}}]]`

### Module 3 : Contrôle de Disponibilité du Stock (Make an API Call)
- Inspecte le bon de livraison créé pour vérifier si tous les articles sont réservés en stock.
- **Modèle :** `stock.picking`
- **Méthode :** `search_read`
- **Paramètres :**
  - `domain` : `[["sale_id", "=", {{sale_order_id}}]]`
  - `fields` : `["id", "name", "state"]`

### Module 4 : Aiguillage selon Disponibilité
- **Cas 1 : Stock réservé (`state == 'assigned'`) :**
  - Envoi d'un message Telegram au client :
    > « ✅ Votre commande {{sale_order_name}} est confirmée ! Vos articles sont disponibles et votre colis est en cours de préparation pour expédition. »
- **Cas 2 : Rupture de stock (`state != 'assigned'`) :**
  - La commande bascule immédiatement vers la **Route 3 (Rupture de stock)**.

