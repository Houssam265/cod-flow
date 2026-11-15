# Route 3 : Rupture de Stock avec Alerte

## 1. Vue d'Ensemble
- **Objectif :** Gérer l'exception où une commande est confirmée par le client mais qu'un ou plusieurs articles ne disposent pas d'un stock physique suffisant dans l'entrepôt.
- **Condition de déclenchement :** L'état du bon de livraison `stock.picking` associé à la commande n'est pas réservé (`state != 'assigned'`).

---

## 2. Déroulement Détaillé des Modules

### Module 1 : Alerte Prioritaire Administrateur Telegram
- Envoie une notification instantanée à l'administrateur de la boutique pour signaler la rupture.
- **Canal :** Telegram Bot.
- **Destinataire :** Identifiant administrateur fixe (`TELEGRAM_ADMIN_CHAT_ID` configuré dans `.env`).
- **Contenu du message :**
  ```text
  ⚠️ ALERTE RUPTURE DE STOCK | COD-Flow

  Commande concernée : {{sale_order_name}}
  Client : {{partner_name}} (Tél: {{partner_phone}})
  Statut du bon de livraison : Non réservé (Rupture)

  👉 Veuillez vérifier les niveaux d'inventaire dans Odoo et initier un réapprovisionnement.
  ```

### Module 2 : Notification de Prévenance au Client
- Envoie un message transparent et rassurant au client sur Telegram pour l'informer du délai supplémentaire :
  ```text
  Bonjour {{client_first_name}} !
  Votre commande {{sale_order_name}} est bien confirmée.
  En raison d'une forte demande sur l'un de vos articles, un délai de préparation supplémentaire de 24h à 48h est nécessaire.
  Nous faisons le maximum pour vous expédier votre colis dans les meilleurs délais. Merci pour votre patience !
  ```

