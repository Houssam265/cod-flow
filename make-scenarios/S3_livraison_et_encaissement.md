# Spécification Technique Make.com - Scénario S3 : Suivi Livraison, Facturation et Encaissement COD

## 1. Vue d'Ensemble
- **Nom du scénario :** `COD-Flow | S3 - Statut Transporteur, Facturation Odoo, Encaissement COD & Relances`
- **Déclencheur :** Détection de modification ou lecture périodique de la feuille Google Sheets Transporteur (`Watch Rows / Webhook Sheets`).
- **Rôle principal :** Synchroniser l'état réel de la livraison remonté par le livreur, clôturer le cycle financier (facturation + paiement automatique) en cas de succès, gérer les relances automatiques J+1 et J+2 en cas d'injoignabilité, et traiter les annulations / retours de stock en cas de refus.

---

## 2. Diagramme Logique du Flux
```
[Feuille Google Sheets Transporteur mise à jour]
                         │
                         ▼
        [Lecture Statut Transporteur]
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   [ "Livré" ]    [ "Injoignable" ]  [ "Refusé" ]
        │                │                │
        │                ├─► J+1 : Relance Telegram 1
        │                │
        │                ├─► J+2 : Relance Ultime 2
        │                │
        │                └─► J+3 : Bascule vers "Refusé"
        │                                 │
        │                                 ▼
        │                    [Annulation Bon Livraison (action_cancel)]
        │                    [Annulation Vente Odoo (action_cancel)]
        │                    [x_statut_livraison = 'refuse']
        │
        ▼
[Validation Bon de Livraison Odoo (button_validate)]
        │
[Génération Facture Client (_create_invoices)]
        │
[Comptabilisation Facture (action_post)]
        │
[Enregistrement Paiement COD (account.payment.register)]
        │
[Mise à jour x_statut_livraison = 'livre']
        │
[Notification Remerciement Telegram Client]
```

---

## 3. Spécification Détaillée des Modules Make

### Module 1 : Déclencheur Transporteur Google Sheets
- **Type :** `Google Sheets > Watch Updated Rows` (ou Webhook déclenché via Google Apps Script)
- **Feuille ciblée :** `Expeditions_COD`
- **Colonnes surveillées :** `Statut Transporteur`, `Tentatives`, `Motif Refus`.
- **Valeurs possibles du statut :**
  - `Livré` : Le client a réceptionné et payé en espèces.
  - `Injoignable` : Le client n'a pas décroché ou était absent lors du passage.
  - `Refusé` : Le client a expressément décliné le colis.

---

### Module 2 : Recherche de la Commande Odoo Associée
- **Modèle Odoo :** `sale.order`
- **Méthode :** `search_read`
- **Arguments (args) :**
  ```json
  [
    [
      ["name", "=", "{{1.numero_commande_odoo}}"]
    ]
  ]
  ```
- **Paramètres nommés (kwargs) :**
  ```json
  {
    "fields": ["id", "name", "partner_id", "amount_total", "picking_ids", "invoice_ids", "x_statut_livraison"]
  }
  ```

---

### Module 3 : Routeur par Statut de Livraison

---

#### 🟢 BRANCHE 1 : STATUT "LIVRÉ" (Encaissement Réussi)

1. **Module 1.1 : Validation du Bon de Livraison (stock.picking)**
   - **Modèle Odoo :** `stock.picking`
   - **Méthode :** `button_validate`
   - **Arguments :** `[[{{picking_id}}]]`
   - **Ce qu'il fait :** Déduit définitivement les produits de l'inventaire physique dans l'entrepôt.

2. **Module 1.2 : Création de la Facture Client (sale.order)**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `_create_invoices`
   - **Arguments :** `[[{{sale_order_id}}]]`
   - **Résultat :** Retourne l'identifiant de la nouvelle facture `invoice_id` (`account.move`).

3. **Module 1.3 : Comptabilisation de la Facture (account.move)**
   - **Modèle Odoo :** `account.move`
   - **Méthode :** `action_post`
   - **Arguments :** `[[{{invoice_id}}]]`
   - **Effet comptable :** La facture passe de l'état `draft` (Brouillon) à `posted` (Comptabilisée).

4. **Module 1.4 : Enregistrement du Paiement Espèces COD (account.payment.register)**
   - **Mécanisme standard Odoo 18 XML-RPC :**
     - **Étape A : Création du wizard de paiement avec contexte de facture :**
       - **Modèle :** `account.payment.register`
       - **Méthode :** `create`
       - **Arguments (valeurs) :**
         ```json
         {
           "amount": {{amount_total}},
           "payment_date": "{{formatDate(now; "YYYY-MM-DD")}}",
           "communication": "Paiement COD {{2.name}}"
         }
         ```
       - **Contexte XML-RPC indispensable :**
         ```json
         {
           "active_model": "account.move",
           "active_ids": [{{invoice_id}}]
         }
         ```
     - **Étape B : Validation du paiement :**
       - **Modèle :** `account.payment.register`
       - **Méthode :** `action_create_payments`
       - **Arguments :** `[[{{wizard_id}}]]`
   - **Résultat dans Odoo :** La facture est marquée avec le ruban vert **"Payé"** !

5. **Module 1.5 : Mise à jour du Statut Odoo**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `write`
   - **Arguments :** `[{{sale_order_id}}], {"x_statut_livraison": "livre"}`

6. **Module 1.6 : Notification Telegram au Client**
   - **Message :**
     ```text
     🎉 Votre commande {{2.name}} a bien été livrée !
     
     Nous confirmons la bonne réception de votre paiement de {{amount_total}} MAD.
     Toute l'équipe vous remercie chaleureusement pour votre confiance et vous souhaite une excellente utilisation de vos produits !
     ```

---

#### 🟡 BRANCHE 2 : STATUT "INJOIGNABLE" (Relances J+1 et J+2)

1. **Module 2.1 : Mise à jour du Statut Odoo**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `write`
   - **Arguments :** `[{{sale_order_id}}], {"x_statut_livraison": "injoignable"}`

2. **Module 2.2 : Incrémentation du Compteur de Tentatives dans Google Sheets**
   - **Type :** `Google Sheets > Update a Row`
   - **Mise à jour :** `Tentatives = {{1.tentatives + 1}}`, `Date Dernier Statut = {{formatDate(now; "YYYY-MM-DD")}}`

3. **Module 2.3 : Routeur selon le Nombre de Tentatives :**
   - **Cas A : Tentative = 1 (Relance J+1)**
     - Envoi d'un message Telegram bienveillant :
       ```text
       Bonjour ! Notre transporteur a tenté de vous livrer aujourd'hui pour votre commande {{2.name}}, mais n'a pas réussi à vous joindre.
       📞 Il se représentera demain. Pouvez-vous nous confirmer que vous serez bien joignable sur votre numéro ?
       ```
   - **Cas B : Tentative = 2 (Relance Ultime J+2)**
     - Envoi d'un message Telegram d'urgence :
       ```text
       ⚠️ Important : Deuxième passage infructueux pour votre colis {{2.name}}.
       Notre livreur effectuera une dernière tentative demain matin. En cas de non-réponse, le colis sera automatiquement réexpédié à l'entrepôt.
       ```
   - **Cas C : Tentative >= 3 (Échec définitif)**
     - Bascule automatique vers la Branche 3 (Refusé / Retour stock).

---

#### 🔴 BRANCHE 3 : STATUT "REFUSÉ" (Retour en Stock et Clôture)

1. **Module 3.1 : Enregistrement du Motif dans Odoo**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `write`
   - **Arguments :**
     ```json
     [{{sale_order_id}}], {
       "x_statut_livraison": "refuse",
       "x_motif_retour": "{{ifempty(1.motif; 'Client injoignable ou refus à la porte')}}"
     }
     ```

2. **Module 3.2 : Annulation du Bon de Livraison (Remise en stock)**
   - **Modèle Odoo :** `stock.picking`
   - **Méthode :** `action_cancel`
   - **Arguments :** `[[{{picking_id}}]]`
   - **Effet :** Les articles réservés sont libérés et réintégrés dans le stock disponible de l'entrepôt.

3. **Module 3.3 : Annulation de la Commande de Vente**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `action_cancel`
   - **Arguments :** `[[{{sale_order_id}}]]`

4. **Module 3.4 : Alerte Telegram au Gérant**
   - **Contenu :**
     ```text
     📦 RETOUR COLIS ENREGISTRÉ | COD-Flow
     
     Commande : {{2.name}}
     Client : {{2.partner_id[1]}}
     Motif : {{1.motif}}
     Articles réintégrés dans l'inventaire physique Odoo.
     ```

---

## 4. Robustesse et Idempotence
- Le scénario vérifie systématiquement `x_statut_livraison` dans Odoo avant d'exécuter la facturation : si le statut est déjà `livre`, le traitement financier est ignoré pour interdire toute double facturation ou double écriture comptable.

