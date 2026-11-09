# Architecture Technique et Fonctionnelle - COD-Flow

## 1. Vision et Problématique Métier
Au Maroc, le commerce en ligne repose à plus de 85% sur le modèle **Cash On Delivery (COD)**, où les transactions s'initient sur les canaux conversationnels (WhatsApp, Telegram, Instagram). 
Ce mode de fonctionnement génère trois goulots d'étranglement critiques pour les e-commerçants :
1. **Saisie manuelle fastidieuse :** Recopier manuellement les messages non structurés (Français, Darija, fautes) dans un ERP prend 3 à 5 minutes par commande.
2. **Erreurs et doublons :** Mauvais numéros de téléphone, oublis d'articles, commandes passées en double créant des surcoûts d'expédition.
3. **Taux d'échec de livraison élevé (20% à 30%) :** Absence de relances automatisées des clients injoignables et retards de synchronisation avec le transporteur.

**COD-Flow** résout l'ensemble de cette chaîne en créant une passerelle automatisée de bout en bout entre la messagerie instantanée, un LLM spécialisé, Make.com, et **Odoo 18 Community**.

---

## 2. Schéma Global d'Architecture (Mermaid)

```mermaid
flowchart TD
    subgraph Canaux["Canaux Clients"]
        TG["Telegram Bot"]
        WA["WhatsApp (Twilio Sandbox)"]
    end

    subgraph Orchestration["Orchestrateur Make.com"]
        S1["S1 : Prise de Commande & Devis"]
        S2["S2 : Confirmation & Stock"]
        S3["S3 : Livraison, Facturation & COD"]
        S4["S4 : Monitoring & Rapport 18h"]
    end

    subgraph IA["Intelligence Artificielle"]
        LLM["LLM Parser (Français / Darija)"]
        SCHEMA["JSON Schema Strict"]
    end

    subgraph ERP["ERP Odoo 18 Community (Docker)"]
        SO["sale.order\n(Devis & Commandes)"]
        PARTNER["res.partner\n(Clients +212)"]
        PROD["product.product\n(Stocks & Articles)"]
        PICK["stock.picking\n(Bons de livraison)"]
        PO["purchase.order\n(Demandes de réassort)"]
        INV["account.move\n(Facturation)"]
        PAY["account.payment\n(Encaissements COD)"]
    end

    subgraph Logistique["Logistique & Transporteur"]
        SHEET["Google Sheets Transporteur\n(Expéditions & Statuts)"]
        LIVREUR["Livreur / Agence COD"]
    end

    subgraph Gestion["Supervision Direction"]
        ADMIN_TG["Canal Telegram Gérant"]
    end

    %% Flux S1
    TG -->|Message client| S1
    WA -->|Message client| S1
    S1 -->|Extraction entités| LLM
    LLM -->|JSON Validé| S1
    S1 -->|Recherche / Création| PARTNER
    S1 -->|Vérification anti-doublon| SO
    S1 -->|Sélection articles| PROD
    S1 -->|Création Devis| SO
    S1 -.->|Notification récapitulative| TG

    %% Flux S2
    TG -->|Confirmation 'OUI'| S2
    S2 -->|action_confirm| SO
    SO -->|Génération| PICK
    S2 -->|Contrôle réservation| PICK
    S2 -- En stock --> SHEET
    S2 -- Rupture --> PO
    S2 -- Alerte Rupture --> ADMIN_TG

    %% Flux S3
    LIVREUR -->|Mise à jour statut| SHEET
    SHEET -->|Watch Rows| S3
    S3 -- Livré --> PICK
    S3 -- Livré --> INV
    INV --> PAY
    S3 -- Injoignable (J+1, J+2) --> TG
    S3 -- Refusé --> SO

    %% Flux S4
    S1 -. Erreur .-> S4
    S2 -. Erreur .-> S4
    S3 -. Erreur .-> S4
    S4 -->|Alerte incident| ADMIN_TG
    S4 -->|Rapport quotidien 18h| ADMIN_TG
    S4 -->|Requêtes KPI XML-RPC| SO
    S4 -->|Contrôle stock minimum| PROD
```

---

## 3. Matrice des Composants et Technologies

| Composant | Technologie / Version | Rôle & Responsabilité |
| :--- | :--- | :--- |
| **Hébergement ERP** | Docker & Docker Compose | Conteneurisation Odoo 18.0 Community et PostgreSQL 16 Alpine |
| **Moteur ERP** | Odoo 18 Community Edition | Gestion des ventes, CRM, gestion de stock par emplacement, facturation et paiements |
| **API Gateway ERP** | XML-RPC standard (`/xmlrpc/2/object`) | Interface sans dépendances externes pour l'automatisation Make et scripts Python |
| **Orchestrateur** | Make.com (Scénarios S1 à S4) | Routage des webhooks, orchestration des flux métier, logique décisionnelle |
| **Moteur LLM** | GPT-4o-mini / Gemini Flash | Extraction sémantique bilingue (Français, Darija, Arabizi) vers JSON strict |
| **Simulateur Logistique** | Google Sheets API | Registre partagé avec le transporteur COD (livré, injoignable, refusé) |
| **Canaux Utilisateurs** | Telegram Bot API / Twilio WhatsApp | Messagerie bidirectionnelle avec les clients finaux |
| **Canal Superviseur** | Telegram Bot API | Alertes d'erreurs en temps réel et diffusion du rapport d'activité quotidien à 18h |

---

## 4. Modèle de Données et Personnalisations Odoo 18

### 4.1 Extensions sur le modèle `sale.order`
Les champs personnalisés suivants sont injectés via `ir.model.fields` :
- `x_canal` (`selection`) : `[('whatsapp', 'WhatsApp'), ('telegram', 'Telegram'), ('instagram', 'Instagram')]`
- `x_message_id` (`char`, `index=True`) : Identifiant unique du message conversationnel, pivot du mécanisme anti-doublon.
- `x_statut_livraison` (`selection`) : `[('en_attente', 'En attente'), ('expedie', 'Expédié'), ('livre', 'Livré'), ('refuse', 'Refusé'), ('injoignable', 'Injoignable')]`
- `x_motif_retour` (`char`) : Raison déclarée du retour (ex: "Client indisponible après 3 relances", "Refus à la porte").

### 4.2 Spécificité Odoo 18 sur `product.template`
Dans Odoo 18, la gestion des produits stockables a évolué :
- Le champ `type` prend la valeur `'consu'` (Consommable / Marchandise).
- Le suivi des stocks est activé via le booléen `'is_storable' = True`.
- Les niveaux de stock physique sont gérés au niveau des variantes `product.product` via `stock.quant`.

---

## 5. Règles de Résilience et Idempotence

1. **Anti-doublon à double verrou :**
   - *Verrou technique :* Unicité du `x_message_id` issu de la messagerie instantanée.
   - *Verrou métier :* Détection des commandes issues du même numéro de téléphone portant sur les mêmes articles enregistrées il y a moins de 24h.
2. **Normalisation téléphonique automatique :**
   - Tout numéro marocain saisi sous format local (`06...`, `07...`, `05...`), international (`212...`, `+212...`) ou avec séparateurs d'espaces est normalisé au format E.164 `+212XXXXXXXXX`.
3. **Idempotence des transactions financières :**
   - La création de facture (`_create_invoices`) et le paiement COD ne peuvent être exécutés qu'une seule fois grâce au contrôle préalable du champ `x_statut_livraison != 'livre'`.

