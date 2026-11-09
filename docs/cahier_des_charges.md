# Cahier des Charges Fonctionnel et Technique - Projet COD-Flow

## 1. Contexte et Objectifs du Projet
Le projet **COD-Flow** s'inscrit dans le cadre d'un Projet de Fin d'Études (PFE) d'ingénierie logicielle spécialisé dans l'écosystème ERP (Odoo / SAP). Il vise à concevoir, déployer et évaluer une architecture d'automatisation intégrale pour les petites et moyennes entreprises marocaines opérant en **Cash On Delivery (COD)**.

### 1.1 Objectifs Clés
- **Automatisation Zéro Saisie :** Réduire le temps de traitement d'une commande reçue par messagerie instantanée à moins de 5 secondes.
- **Fiabilité des Données :** Éliminer les erreurs de retranscription manuelle grâce à un parseur sémantique LLM spécialisé pour le dialecte marocain (Darija / Arabizi) et le Français.
- **Optimisation de la Délivrance COD :** Réduire le taux de retour des colis (actuellement estimé entre 20% et 30% au Maroc) grâce à un cycle automatisé de relances ciblées à J+1 et J+2 pour les clients injoignables.
- **Bouclage Comptable Immédiat :** Clôturer automatiquement le cycle logistique et financier dans l'ERP dès la notification de remise des espèces par le transporteur.

---

## 2. Périmètre Fonctionnel

### Module F1 : Réception Multi-Canale et Extraction Sémantique
- Capture des messages textuels entrants depuis Telegram ou WhatsApp.
- Extraction normalisée des entités :
  - Identité du client (`nom`).
  - Coordonnées téléphoniques au format marocain (`telephone`).
  - Ville de livraison normalisée (`ville`).
  - Adresse physique détaillée (`adresse`).
  - Articles commandés et quantités (`articles[{reference_ou_nom, quantite}]`).
- Détection des commandes incomplètes et génération automatique de messages de clarification.

### Module F2 : Intégration ERP Odoo 18
- Contrôle strict anti-doublon (message ID unique et fenêtre temporelle de 24h).
- Déduplication et création automatique du contact client (`res.partner`) avec numéro formaté `+212`.
- Correspondance dynamique des articles avec le catalogue de produits (`product.product`).
- Création du devis (`sale.order`) et notification d'arbitrage au client.

### Module F3 : Gestion des Stocks et Logistique COD
- Confirmation de la commande (`action_confirm`) sur validation client.
- Contrôle de la disponibilité physique en stock (`action_assign`).
- Déclenchement automatique d'une demande de prix fournisseur (`purchase.order`) en cas de rupture de stock.
- Synchronisation bidirectionnelle avec la feuille de route du transporteur (Google Sheets).

### Module F4 : Clôture Financière et Encaissement
- Traitement en temps réel des trois statuts logistiques :
  - **Livré :** Validation du bon de livraison (`button_validate`), création de facture (`_create_invoices`), validation comptable (`action_post`), enregistrement du paiement espèces COD (`account.payment.register`).
  - **Injoignable :** Protocole de relances automatiques J+1 et J+2 avec message d'avertissement.
  - **Refusé :** Annulation du bon de livraison, réintégration en stock et annulation de la vente.

### Module F5 : Monitoring et Reporting Exécutif
- Journalisation centralisée des requêtes et erreurs.
- Diffusion d'un rapport quotidien automatisé à 18h00 sur Telegram récapitulant :
  - Volume de commandes traitées.
  - Taux de confirmation et de délivrance.
  - Chiffre d'Affaires total encaissé en espèces.
  - Alertes de seuil de stock minimum.

---

## 3. Spécifications Techniques et Contraintes

### 3.1 Environnement et Stack Logicielle
- **ERP :** Odoo 18.0 Community Edition déployé sous conteneur Docker officiel.
- **Base de Données :** PostgreSQL 16 Alpine conteneurisé avec volumes persistants.
- **Protocoles d'Intégration :** XML-RPC standard via `/xmlrpc/2/common` et `/xmlrpc/2/object`.
- **Orchestration de Flux :** Make.com (scénarios modulaires S1, S2, S3, S4).
- **Moteur d'IA :** Modèle de langage avec Structured Outputs (GPT-4o-mini / Gemini Flash).
- **Langage de Scripting :** Python 3 (bibliothèque standard uniquement pour garantir l'indépendance de déploiement).

### 3.2 Sécurité et Confidentialité
- **Gestion des Secrets :** Aucun mot de passe, jeton ou clé d'API ne doit figurer dans le code source versionné. Utilisation exclusive du fichier `.env` protégé par `.gitignore`.
- **Conformité des Données Personnelles :** Traitement des numéros de téléphone et adresses conforme aux recommandations de protection des données (CNDP au Maroc).
- **Isolation :** Déploiement local sur réseau Docker fermé avec exposition stricte des ports requis (8069 pour le serveur web/API).

---

## 4. Critères d'Acceptation et Livrables
1. **Livrable 1 : Infrastructure Odoo Docker** opérationnelle via un fichier `docker-compose.yml` reproductible en une seule commande.
2. **Livrable 2 : Scripts Python d'initialisation** idempotents, documentés et validés par un script de contrôle global (`check_setup.py`).
3. **Livrable 3 : Fiches de spécification Make** exhaustives décrivant chaque module, mapping et route d'exception pour les 4 scénarios.
4. **Livrable 4 : Dataset d'évaluation LLM** comportant au minimum 20 messages de test diversifiés (Français, Darija, ambigus, ruptures, doublons).
5. **Livrable 5 : Cadre de mesure expérimentale** permettant de comparer la saisie manuelle et l'automatisation COD-Flow sur des métriques réelles.

