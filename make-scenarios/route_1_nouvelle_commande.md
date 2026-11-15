# Route 1 : Nouvelle Commande (Gemini, Client Odoo, Devis)

## 1. Vue d'Ensemble
- **Objectif :** Réceptionner un message client informel (Français / Darija), extraire les données de commande via Gemini (modèle Flash, gemini-3.6-flash) (offre gratuite), contrôler les doublons (10 minutes), créer ou retrouver le client Odoo et générer un devis `sale.order`.
- **Filtre de route Make :** Le message ne correspond ni à `"oui"` (confirmation) ni à `"livré..."` (livraison).

---

## 2. Déroulement Détaillé des Modules

### Module 1 : Webhook Telegram
- Reçoit le message entrant du client avec `text`, `chat.id`, `from.first_name`, `date`.

### Module 2 : Extraction Sémantique via Gemini API
- **Fournisseur :** Google AI Studio / Gemini API (Gemini (modèle Flash, gemini-3.6-flash), offre gratuite).
- **Prompt système :**
  - Contient les règles d'extraction bilingue (Français et Darija translittérée).
  - **Catalogue produit intégré directement dans le prompt :**
    - `COD-ARGAN-01` : Huile d'Argan Pure Bio 100ml (150 MAD)
    - `COD-SAVON-02` : Savon Noir Traditionnel 250g (45 MAD)
    - `COD-PACK-03` : Pack Hammam Royal (120 MAD)
    - `COD-SAFRAN-04` : Safran Pur de Taliouine 1g (70 MAD)
    - `COD-SERUM-05` : Sérum Anti-Âge Figue de Barbarie 30ml (220 MAD)
- **Sortie :** JSON strict avec `nom`, `telephone`, `ville`, `adresse`, `articles[{code, quantite, prix}]`.

### Module 3 : Parseur JSON
- Convertit le texte JSON de Gemini en variables Make exploitables.

### Module 4 : Contrôle Anti-Doublon (10 minutes)
- Vérifie si une commande identique pour ce même numéro de téléphone a été initiée au cours des **10 dernières minutes**.
- Si un doublon est détecté : envoi d'un message Telegram d'information et arrêt de la route.

### Module 5 : Recherche Client Odoo (Make an API Call)
- **Modèle :** `res.partner`
- **Méthode :** `search_read`
- **Paramètres :**
  - `domain` : `[["phone", "=", "{{telephone}}"]]`
  - `fields` : `["id", "name", "phone"]`

### Module 6 : Création Client Odoo (si absent) (Make an API Call)
- **Condition :** Aucun client trouvé au module 5.
- **Modèle :** `res.partner`
- **Méthode :** `create`
- **Paramètres :**
  ```json
  [
    {
      "name": "{{nom}}",
      "phone": "{{telephone}}",
      "street": "{{adresse}}",
      "city": "{{ville}}",
      "customer_rank": 1
    }
  ]
  ```

### Module 7 : Création du Devis Odoo (Make an API Call)
- **Modèle :** `sale.order`
- **Méthode :** `create`
- **Paramètres :**
  ```json
  [
    {
      "partner_id": {{partner_id}},
      "client_order_ref": "{{telegram_chat_id}}",
      "order_line": [
        [0, 0, {
          "product_id": {{product_id}},
          "product_uom_qty": {{quantite}},
          "price_unit": {{prix}}
        }]
      ]
    }
  ]
  ```
- *Note d'implémentation :* L'identifiant de chat Telegram (`chat_id`) est stocké dans le champ `client_order_ref` du devis Odoo (`sale.order`), ce qui permet de réidentifier la commande du client lors de la confirmation sans nécessiter de base de données externe.
- Récupère l'identifiant et la référence du devis généré (ex: `S00012`).

### Module 8 : Envoi du Récapitulatif Telegram
- Message envoyé sur Telegram au client :
  - Référence du devis (ex: `S00012`).
  - Détail des articles, quantités et total en MAD.
  - Adresse de livraison enregistrée.
  - **Consigne de validation :** *« Pour confirmer votre commande, répondez simplement OUI à ce message. »*

