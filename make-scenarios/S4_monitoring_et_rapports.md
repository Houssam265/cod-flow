# Spécification Technique Make.com - Scénario S4 : Monitoring, Alertes et Rapport Quotidien

## 1. Vue d'Ensemble
- **Nom du scénario :** `COD-Flow | S4 - Supervision Continue & Rapport Journalier 18h`
- **Déclencheurs :**
  1. **En temps réel :** Webhook interne de gestion d'erreur (Error Handler Trigger) appelé dès qu'un scénario S1, S2 ou S3 subit un échec critique.
  2. **Planifié à 18h00 (Heure de Casablanca / GMT+1) :** Déclencheur cron Make quotidien.
- **Rôle principal :** Garantir la surveillance proactive de l'infrastructure ERP, notifier le gérant en cas d'anomalie bloquante et consolider les performances opérationnelles et financières du Cash On Delivery à la fin de chaque journée.

---

## 2. Diagramme Logique du Flux
```
[Déclencheur Temps Réel (Erreur S1/S2/S3)] ──► [Formatage Alerte Urgence] ──► [Telegram Admin]

[Déclencheur Quotidien 18h00]
              │
              ▼
[Requêtes Odoo XML-RPC : Activité de la Journée]
              │
              ├─► Nombre de commandes reçues (sale.order)
              ├─► Nombre de commandes confirmées (state = sale)
              ├─► Nombre de colis livrés & CA COD encaissé (x_statut_livraison = livre)
              ├─► Nombre de retours / refus (x_statut_livraison = refuse)
              ├─► Nombre de clients injoignables en cours de relance
              └─► Vérification des alertes de stock critique (orderpoint)
              │
              ▼
[Calcul des KPI : Taux de Livraison, Taux de Retour, Total MAD Encaissé]
              │
              ▼
[Envoi du Rapport Exécutif sur le Canal Telegram Direction]
```

---

## 3. Spécification Détaillée des Modules Make

### PARTIE A : Traitement des Alertes d'Erreurs en Temps Réel

#### Module A.1 : Webhook d'Erreur (Internal Error Receiver)
- **Type :** `Webhooks > Custom webhook`
- **Reçoit le payload d'erreur standardisé de Make :**
  ```json
  {
    "scenario_source": "S1_prise_de_commande",
    "module_id": 9,
    "module_type": "Odoo XML-RPC Create",
    "error_message": "Fault 1: 'Record does not exist or has been deleted.'",
    "timestamp": "2026-11-09T18:30:00Z",
    "input_data": {
      "partner_phone": "+212661234567",
      "articles": ["Huile d'Argan"]
    }
  }
  ```

#### Module A.2 : Notification d'Urgence au Gérant (Telegram Admin)
- **Type :** `Telegram Bot > Send Text Message`
- **Destinataire :** `{{env.TELEGRAM_ADMIN_CHAT_ID}}`
- **Contenu :**
  ```text
  🚨 ALERTE SYSTÈME | COD-Flow Incident

  Origine : Scénario {{scenario_source}}
  Module défaillant : {{module_type}} (ID: {{module_id}})
  Erreur : {{error_message}}
  Heure : {{formatDate(timestamp; "YYYY-MM-DD HH:mm:ss")}}

  Données concernées :
  {{JSON.stringify(input_data)}}

  👉 Intervention manuelle recommandée dans l'interface Make ou Odoo.
  ```

---

### PARTIE B : Rapport Quotidien d'Activité à 18h00

#### Module B.1 : Planificateur Make
- **Type :** `Schedule > Every day`
- **Heure :** `18:00`
- **Fuseau horaire :** `Africa/Casablanca`

---

#### Module B.2 : Requêtes Odoo XML-RPC de Synthèse

1. **Requête 1 : Commandes reçues aujourd'hui**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `search_count`
   - **Arguments :**
     ```json
     [
       [["date_order", ">=", "{{formatDate(setHour(setMinute(now; 0); 0); "YYYY-MM-DD HH:mm:ss")}}"]]
     ]
     ```
   - **Résultat :** `nb_commandes_recues`

2. **Requête 2 : Commandes confirmées et expédiées**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `search_count`
   - **Arguments :**
     ```json
     [
       [
         ["state", "in", ["sale", "done"]],
         ["date_order", ">=", "{{formatDate(setHour(setMinute(now; 0); 0); "YYYY-MM-DD HH:mm:ss")}}"]
       ]
     ]
     ```
   - **Résultat :** `nb_commandes_confirmees`

3. **Requête 3 : Livraisons réussies et CA encaissé**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `search_read`
   - **Arguments (args) :**
     ```json
     [
       [
         ["x_statut_livraison", "=", "livre"],
         ["write_date", ">=", "{{formatDate(setHour(setMinute(now; 0); 0); "YYYY-MM-DD HH:mm:ss")}}"]
       ]
     ]
     ```
   - **Paramètres nommés (kwargs) :**
     ```json
     {
       "fields": ["id", "name", "amount_total"]
     }
     ```
   - **Agrégation :**
     - `nb_livrees = length(result)`
     - `ca_encaisse_mad = sum(map(result; "amount_total"))`

4. **Requête 4 : Refus et retours enregistrés**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `search_read`
   - **Arguments (args) :**
     ```json
     [
       [
         ["x_statut_livraison", "=", "refuse"],
         ["write_date", ">=", "{{formatDate(setHour(setMinute(now; 0); 0); "YYYY-MM-DD HH:mm:ss")}}"]
       ]
     ]
     ```
   - **Paramètres nommés (kwargs) :**
     ```json
     {
       "fields": ["id", "name", "x_motif_retour"]
     }
     ```
   - **Résultat :** `nb_refusees = length(result)`

5. **Requête 5 : Clients injoignables en cours de relance**
   - **Modèle Odoo :** `sale.order`
   - **Méthode :** `search_count`
   - **Arguments (args) :**
     ```json
     [
       [
         ["x_statut_livraison", "=", "injoignable"]
       ]
     ]
     ```
   - **Résultat :** `nb_injoignables`

6. **Requête 6 : Alertes de stock minimum**
   - **Modèle Odoo :** `stock.warehouse.orderpoint`
   - **Méthode :** `search_read`
   - **Arguments (args) :**
     ```json
     [
       [
         ["qty_on_hand", "<=", "product_min_qty"]
       ]
     ]
     ```
   - **Paramètres nommés (kwargs) :**
     ```json
     {
       "fields": ["product_id", "qty_on_hand", "product_min_qty"]
     }
     ```
     ```json
     [
       [["qty_on_hand", "<=", "product_min_qty"]]
     ],
     ["product_id", "qty_on_hand", "product_min_qty"]
     ```
   - **Résultat :** Liste des références en alerte critique `stocks_critiques[]`.

---

#### Module B.3 : Calcul des Indicateurs de Performance (KPI)
- **Taux de Confirmation :** `round((nb_commandes_confirmees / nb_commandes_recues) * 100, 1) %`
- **Taux de Livraison (Délivrance) :** `round((nb_livrees / (nb_livrees + nb_refusees)) * 100, 1) %`
- **Taux de Retour COD :** `round((nb_refusees / (nb_livrees + nb_refusees)) * 100, 1) %`

---

#### Module B.4 : Diffusion du Rapport Quotidien sur Telegram
- **Type :** `Telegram Bot > Send Text Message`
- **Destinataire :** `{{env.TELEGRAM_ADMIN_CHAT_ID}}`
- **Mise en forme Markdown :**
  ```text
  📊 RAPPORT D'ACTIVITÉ QUOTIDIEN | COD-Flow
  📅 Date : {{formatDate(now; "DD/MM/YYYY")}} à 18h00

  📈 1. Volume des Commandes
  • Commandes reçues aujourd'hui : {{nb_commandes_recues}}
  • Commandes confirmées : {{nb_commandes_confirmees}}
  • Taux de confirmation : {{taux_confirmation}} %

  🚚 2. Suivi des Livraisons & Encaissements COD
  • Colis livrés avec succès : {{nb_livrees}} ✅
  • Colis refusés / retours : {{nb_refusees}} ❌
  • Clients injoignables (relances en cours) : {{nb_injoignables}} ⏳
  • Taux de délivrance : {{taux_livraison}} %
  • Taux de retour : {{taux_retour}} %

  💰 3. Bilan Financier COD
  • Chiffre d'Affaires encaissé en espèces : {{ca_encaisse_mad}} MAD 💵

  ⚠️ 4. Alertes Stocks Entrepôt
  {{if(length(stocks_critiques) > 0; 
       join(map(stocks_critiques; "• " + product_id[1] + " : " + qty_on_hand + " u. (Seuil min: " + product_min_qty + ")"); newline); 
       "Tous les niveaux de stock sont conformes. ✅")}}

  COD-Flow | Automatisation ERP & Logistique Odoo 18
  ```

---

## 4. Tolérance aux Pannes
- Si Odoo est temporairement indisponible lors de l'exécution à 18h :
  - Directive `Break` de Make reprogramme la tentative 15 minutes plus tard (18h15).
  - Si l'indisponibilité persiste à 18h30, une alerte est transmise au gérant indiquant l'indisponibilité du serveur Odoo.

