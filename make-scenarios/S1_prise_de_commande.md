# Spécification Technique Make.com - Scénario S1 : Prise de Commande et Création de Devis

## 1. Vue d'Ensemble
- **Nom du scénario :** `COD-Flow | S1 - Reception Message & Creation Devis Odoo`
- **Déclencheur :** Webhook instantané (Custom Webhook Make) connecté à Telegram Bot / WhatsApp Business.
- **Rôle principal :** Extraire les entités via LLM, normaliser le numéro marocain, contrôler les doublons, créer ou lier le client Odoo, mapper les articles et générer un devis de vente (`sale.order`) dans Odoo 18.
- **Délai d'exécution moyen visé :** < 5 secondes.

---

## 2. Diagramme Logique du Flux
```
[Webhook Entrant] 
       │
       ▼
[Appel LLM & Parsing JSON]
       │
       ├─► [Champs manquants ?] ──► OUI ──► [Message de relance client] ──► [Fin]
       │
      NON
       │
       ▼
[Normalisation Téléphone (+212)]
       │
       ▼
[Vérification Anti-doublon Odoo]
       │
       ├─► [Doublon détecté ?] ──► OUI ──► [Notification doublon client] ──► [Fin]
       │
      NON
       │
       ▼
[Recherche / Création Client Odoo (res.partner)]
       │
       ▼
[Résolution Références Produits Odoo (product.product)]
       │
       ▼
[Création Devis Odoo (sale.order)]
       │
       ▼
[Notification Récapitulative Telegram au Client]
```

---

## 3. Spécification Détaillée des Modules Make

### Module 1 : Webhook Entrant (Custom Webhook)
- **Type :** `Webhooks > Custom webhook`
- **Reçoit :**
  ```json
  {
    "source": "telegram",
    "x_message_id": "TG-987654321-12345",
    "sender": {
      "id": "123456789",
      "username": "client_ma",
      "first_name": "Youssef"
    },
    "raw_text": "Bonjour je veux 2 huiles dargan et 1 savon noir Youssef El Amrani 0661234567 Casa Maarif"
  }
  ```
- **Ce qu'il fait :** Réceptionne le payload HTTP POST et initialise la transaction Make.
- **Route d'erreur :** `Ignore` si payload vide, sinon `Break` (3 tentatives avec intervalle exponentiel).

---

### Module 2 : Extraction Intelligente LLM
- **Type :** `OpenAI / Claude / Gemini > Create a Chat Completion` (ou `HTTP > Make a request`)
- **Paramètres :**
  - **Model :** `gpt-4o-mini` (ou `gemini-1.5-flash`)
  - **System Prompt :** Contenu strict de `llm/prompt_extraction.md`
  - **User Message :** `{{1.raw_text}}`
  - **Response Format :** `json_object`
- **Ce qu'il fait :** Déchiffre le message (Français / Darija), identifie les articles, le nom, le numéro, la ville, l'adresse et liste les éventuels champs manquants.
- **Route d'erreur :** `Resume` vers module d'alerte admin (S4).

---

### Module 3 : Parse JSON
- **Type :** `JSON > Parse JSON`
- **Reçoit :** Sortie brute du module 2 (`choices[].message.content`).
- **Schéma appliqué :** Conforme à `llm/schema.json`.
- **Champs produits :**
  - `nom` (String ou null)
  - `telephone` (String ou null)
  - `ville` (String ou null)
  - `adresse` (String ou null)
  - `articles[]` (Array d'objets `reference_ou_nom`, `quantite`)
  - `champs_manquants[]` (Array de Strings)

---

### Module 4 : Routeur Décisionnel (Filtre Complétude)
- **Condition de branchement :**
  - **Branche A (Incomplet) :** `length(3.champs_manquants) > 0`
  - **Branche B (Complet) :** `length(3.champs_manquants) == 0`

#### Branche A : Gestion des Informations Manquantes
- **Action :** Envoi d'un message Telegram interactif au client listant les champs requis :
  - *Exemple de message généré dynamiquement :*
    > "Salam ! Merci pour votre commande. Pour que notre livreur puisse vous livrer dans les meilleures conditions, merci de nous préciser : {{join(3.champs_manquants, ', ')}}."
- **Fin de la branche.**

---

### Module 5 : Normalisation Téléphone (Format +212)
- **Type :** `Tools > Set Variable`
- **Nom :** `normalized_phone`
- **Formule Make :**
  ```text
  if(startsWith(replace(replace(3.telephone; " "; ""); "-"; ""); "0"); 
     replace(replace(replace(3.telephone; " "; ""); "-"; ""); "0"; "+212"); 
     if(startsWith(3.telephone; "212"); 
        "+" + replace(replace(3.telephone; " "; ""); "-"; ""); 
        3.telephone
     )
  )
  ```
- **Résultat garanti :** Format E.164 marocain `+212XXXXXXXXX` (ex: `+212661234567`).

---

### Module 6 : Contrôle Anti-Doublon Odoo XML-RPC
- **Type :** `HTTP > Make a request` (Appel XML-RPC `/xmlrpc/2/object`)
- **Modèle Odoo :** `sale.order`
- **Méthode :** `search_read`
- **Arguments (args) :**
  ```json
  [
    [
      "|",
      ["x_message_id", "=", "{{1.x_message_id}}"],
      "&",
      ["partner_id.phone", "=", "{{5.normalized_phone}}"],
      ["state", "not in", ["cancel"]],
      ["date_order", ">=", "{{addHours(now; -24)}}"]
    ]
  ]
  ```
- **Paramètres nommés (kwargs) :**
  ```json
  {
    "fields": ["id", "name", "x_message_id", "date_order", "amount_total"]
  }
  ```
- **Filtre Make après le module :**
  - Si le tableau retourné contient au moins 1 commande :
    - Envoi d'un message Telegram : *"Bonjour, votre commande [{{name}}] a déjà été enregistrée il y a moins de 24h et est en préparation !"*
    - Arrêt immédiat de la branche pour empêcher la duplication.

---

### Module 7 : Recherche ou Création du Client Odoo
- **Étape 7.1 : Recherche Client existant**
  - **Modèle Odoo :** `res.partner`
  - **Méthode :** `search`
  - **Arguments (args) :**
    ```json
    [
      [
        "|",
        ["phone", "=", "{{5.normalized_phone}}"],
        ["mobile", "=", "{{5.normalized_phone}}"]
      ]
    ]
    ```
- **Étape 7.2 : Création si absent (Filtre `total == 0`)**
  - **Modèle Odoo :** `res.partner`
  - **Méthode :** `create`
  - **Arguments (args) :**
    ```json
    [
      {
        "name": "{{ifempty(3.nom; 'Client Inconnu')}}",
        "phone": "{{5.normalized_phone}}",
        "mobile": "{{5.normalized_phone}}",
        "street": "{{3.adresse}}",
        "city": "{{3.ville}}",
        "customer_rank": 1,
        "comment": "Créé automatiquement par COD-Flow via Telegram"
      }
    ]
    ```
- **Variable de sortie :** `final_partner_id` (soit l'ID existant, soit le nouvel ID créé).

---

### Module 8 : Résolution des Lignes d'Articles (Iterator & Search)
- **Type :** `Iterator` sur `3.articles[]`
- **Pour chaque article :**
  - **Modèle Odoo :** `product.product`
  - **Méthode :** `search_read`
  - **Arguments (args) :**
    ```json
    [
      [
        "|",
        ["default_code", "ilike", "{{item.reference_ou_nom}}"],
        ["name", "ilike", "{{item.reference_ou_nom}}"]
      ]
    ]
    ```
  - **Paramètres nommés (kwargs) :**
    ```json
    {
      "fields": ["id", "name", "default_code", "list_price"]
    }
    ```
- **Type :** `Array Aggregator`
  - **Structure d'agrégation pour Odoo `order_line` (Commande tuple XML-RPC `(0, 0, dict)`) :**
    ```json
    [0, 0, {
      "product_id": {{product_id}},
      "product_uom_qty": {{item.quantite}},
      "price_unit": {{product_price}}
    }]
    ```

---

### Module 9 : Création du Devis Odoo (sale.order)
- **Modèle Odoo :** `sale.order`
- **Méthode :** `create`
- **Arguments (Payload XML-RPC) :**
  ```json
  {
    "partner_id": {{final_partner_id}},
    "x_canal": "{{1.source}}",
    "x_message_id": "{{1.x_message_id}}",
    "x_statut_livraison": "en_attente",
    "order_line": {{aggregated_order_lines}}
  }
  ```
- **Résultat :** Récupération de l'identifiant du devis `sale_order_id`.
- **Lecture du devis créé :**
  - **Modèle :** `sale.order`, **Méthode :** `read`, **Args :** `[{{sale_order_id}}], ["name", "amount_total"]`.

---

### Module 10 : Notification et Demande de Confirmation Telegram
- **Type :** `Telegram Bot > Send a Text Message or Reply`
- **Destinataire :** `{{1.sender.id}}`
- **Contenu du message :**
  ```text
  ✨ Merci pour votre commande sur notre boutique !

  📋 Référence : {{name}}
  📦 Articles commandés :
  {{join(map(3.articles; "reference_ou_nom + ' (x' + quantite + ')'"); newline)}}

  📍 Adresse de livraison :
  {{3.adresse}}, {{3.ville}}
  📞 Contact : {{5.normalized_phone}}

  💰 Montant total à payer à la livraison : {{amount_total}} MAD

  👉 Pour confirmer définitivement l'expédition, veuillez répondre OUI à ce message.
  ```

---

## 4. Stratégie de Résilience et Gestion des Erreurs
1. **Erreur de connexion Odoo (Timeout / Réseau) :**
   - Directive `Break` avec 3 tentatives espacées de 1 min.
   - Si l'erreur persiste : Envoi d'une alerte immédiate au gérant via S4 et notification d'attente au client (*"Un instant s'il vous plaît, notre système enregistre votre commande..."*).
2. **Article non trouvé dans le catalogue Odoo :**
   - Si la recherche `product.product` ne retourne aucun résultat :
     - Utilisation d'un article générique *"Article Non Référencé - À qualifier"* avec prix 0.
     - Ajout d'une étiquette d'alerte sur la commande pour examen manuel prioritaire.

