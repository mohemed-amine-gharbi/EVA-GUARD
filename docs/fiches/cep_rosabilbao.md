# Fiche de lecture — Rosa-Bilbao et al. (2026), DCEP edge-fog-cloud

> ATTENTION : la référence annoncée dans la consigne (Rosa-Bilbao et al. 2025, « surveillance temps réel de blockchains », Computer Standards & Interfaces 91, 103882) ne correspond PAS au PDF fourni. La première page du PDF indique un autre article (voir section 1). Il ne traite pas de blockchain. La fiche décrit fidèlement le PDF fourni ; les liens avec EVA-Guard sont des analogies de notre part, pas des affirmations de l'article.

## 1. Référence exacte et problème visé

J. Rosa-Bilbao, A. Guitarte-Fernández, J. Boubeta-Puig, « A distributed complex event processing system for scalable efficient event detection in intelligent environments », *Computing* (Springer), vol. 108, article 128, 2026 (reçu 4 nov. 2025, accepté 5 juil. 2026, en ligne 3 août 2026), DOI 10.1007/s00607-026-01713-1, 23 pages (p. 1). Les auteurs affirment une contribution égale.
Problème visé : un moteur CEP centralisé peut devenir un goulot d'étranglement quand des capteurs IoT nombreux, dispersés et hétérogènes produisent des événements en continu (p. 1-2). Les auteurs proposent un système CEP distribué (DCEP) en trois couches edge-fog-cloud et l'évaluent sur du matériel léger ARM et un serveur (p. 1-2).

## 2. Architecture

Cadre CEP (Fig. 1, p. 4) : trois phases, capture, analyse (moteur CEP qui confronte les événements aux patterns), réponse (envoi des événements complexes aux consommateurs : mail, broker de messages, actions). Fig. 2 (p. 4-5) : schéma générique DCEP (moteurs CEP interconnectés) ; son contenu détaillé est illisible dans le texte extrait (non vérifié).

Architecture proposée (Fig. 3, p. 9 ; texte §4.1, p. 8) :
- Entrée, couche Edge : capteurs IoT, appareils ou simulateurs qui publient des événements simples dans des topics Kafka, regroupés par « domaines d'application » (ex. hôpitaux, stations météo dans une ville intelligente).
- Traitement, couche Fog : moteurs CEP proches des sources ; chacun consomme seulement les événements simples de son domaine/sous-ensemble de types et produit des événements complexes de niveau domaine (quand un pattern EPL est satisfait).
- Sortie, couche Cloud : moteur(s) CEP qui consomment les événements complexes des nœuds fog, les corrèlent entre domaines et publient des alertes de plus haut niveau vers utilisateurs/systèmes externes (via un broker de sortie, un topic par type d'événement complexe, Fig. 3).
- Contrainte indiquée sur la Fig. 3 : un même pattern ne doit pas être sur deux machines (sinon doublons ; p. 10, sauf réplication + déduplication explicites).

Modèle formel (§4.2, p. 8-10) : fog fi(S(Ei), Pi) → Gi (éq. 1) ; cloud cj(S(Gj), PCj) → Aj (éq. 2) ; latence d'une alerte approximée par la somme des sauts edge→broker, broker→fog, traitement fog, fog→broker, broker→cloud, traitement cloud, cloud→consommateur (éq. 3). Les auteurs notent que la distribution réduit la charge d'un moteur mais peut ajouter de la latence par les sauts réseau (p. 10).

Allocation des tâches (§4.3, p. 10) : pilotée par configuration, statique avant déploiement (selon type d'événement, domaine, capacité du dispositif) ; pas d'algorithme d'équilibrage ou d'ordonnancement automatique.

Technologies (§4.4, p. 10-11 ; §5.2, p. 12 ; §6.3, p. 16) :
- Broker : Apache Kafka (topics persistants, rejouables, groupes de consommateurs) ; MQTT cité comme alternative légère, écartée.
- Moteur CEP : Esper (EPL, fenêtres, opérateurs de pattern, Java, x86 et ARM, intégration EsperIO Kafka) ; Siddhi cité comme alternative.
- Application : un même JAR Java sur tous les nœuds, événements/patterns/topics externalisés en fichiers de configuration ; composant « FlowController » qui publie les événements complexes dans des topics Kafka nommés ; routage par topic selon le type d'événement.
- Collecteurs/simulateurs : producteur et consommateur d'événements en Python (Table 5, p. 15), événements JSON avec deux attributs obligatoires : timestamp (epoch) et SensorId.
- Matériel : Raspberry Pi 4 (BCM2711, 4 coeurs Cortex-A72, 4 Go), Orange Pi 5 (RK3588S, 8 coeurs, 16 Go), un serveur (caractéristiques du serveur : non vérifié, non données dans le texte lu).

Types d'événements et patterns (cas d'étude hôpital, §5.2, Fig. 4 p. 13, Tables 2-4 p. 14-15) :
- Simples (edge) : HospitalFridgeTemp, HospitalLabTemp, schéma timestamp, sensorId, value, unit (Celsius ou Kelvin).
- Complexes (fog) : HospitalFridgeHighTemp, HospitalFridgeLowTemp, HospitalLabHighTemp, HospitalLabLowTemp.
- Alertes (cloud) : HospitalFridgeAlert, HospitalLabAirConditionerAlert, HospitalFireAlert.
- Règles fog (Table 3) : haute = valeur > 7 °C ou > 280 K ; basse = valeur < 0 °C ou < 273 K (frigo et labo, mêmes seuils).
- Règles cloud (Table 4) : FridgeAlert dès qu'un événement haut ou bas du frigo arrive ; LabAirConditionerAlert sur événement bas du labo ; FireAlert quand FridgeHighTemp et LabHighTemp sont corrélés (un pattern symétrique couvre l'ordre d'arrivée inverse, p. 14).
- Listings 1 et 2 (code EPL) : cités p. 12 et 14 mais absents du texte extrait ; code EPL non vérifié.

## 3. Données et évaluation

- Cas d'usage : hôpital intelligent (température d'un frigo à médicaments et température ambiante d'un laboratoire), §5.1, p. 12.
- Blockchains surveillées : aucune. Données : valeurs de capteurs simulées par des producteurs Python (§6.6, p. 19), pas de données réelles.
- Tests fonctionnels/intégration (Table 6, p. 16) : génération, format JSON, transmission Kafka, détection CEP : résultats qualitatifs, sans chiffres.
- Métriques : débit, latence de bout en bout (moyenne, médiane, p95), débit de sortie d'alertes, CPU, mémoire (p. 2, 16-19).
- Stress test distribué (Table 7, p. 17, 10 000 000 d'événements par charge) : charge 10 000 ev/s → 12 870 ev/s traités ; 100 000 → 39 841 ; 500 000 → 57 471 ; 1 000 000 → 68 027 (pic) ; 1 500 000 → 60 241 (saturation, p. 16).
- Comparaison contrôlée (Table 8, p. 18 ; 3 répétitions, 5 000 événements par type, 100 à 2000 ev/s ; seules HospitalFridgeAlert et HospitalLabAlert comparées ; FireAlert exclue car dépendante de l'ordre) :
  - Nombre d'alertes de haut niveau identique dans les deux modes : 4937 à chaque débit.
  - Centralisé (1 Orange Pi 5), latence moyenne : 9072,17 ms à 100 ev/s ; 43 579,66 ms à 2000 ev/s ; p95 à 2000 ev/s : 65 378,33 ms ; débit de sortie 45,09 à 86,12 alertes/s.
  - Distribué, latence moyenne : 1026,50 ms à 100 ev/s ; 1859,69 ms à 2000 ev/s ; p95 à 2000 ev/s : 6987,67 ms ; débit de sortie 45,48 (100 ev/s) à 775,21 alertes/s (2000 ev/s).
- Ressources (Table 9, p. 19) : centralisé Orange Pi CPU moyen 15,48 % / max 62,74 % / mém. 5,61 % ; distribué serveur cloud 40,37 / 84,00 / 78,17 ; fog Raspberry Pi 31,90 / 100,00 / 17,08 ; fog Orange Pi 15,10 / 56,59 / 5,41.
- Conclusion des auteurs (p. 19) : le DCEP est utile quand le traitement se décompose par domaine et se place sur des nœuds hétérogènes ; pas de bénéfice généralisé.

## 4. Forces et limites

Forces
1. Évaluation chiffrée et reproductible : 3 répétitions, mêmes broker/flux/patterns dans les deux déploiements (§6.4, p. 17), artefacts publiés sur Zenodo (p. 20).
2. Conception configurable : types d'événements, topics et patterns EPL externalisés, même JAR pour fog et cloud (§4.3-4.4, p. 10-11) ; routage par topic qui limite les données reçues par chaque moteur.
3. Honnêteté des auteurs : ne prétendent pas que la distribution réduit toujours la latence (p. 3, p. 10) ; exclusion justifiée de FireAlert de la comparaison (p. 17) ; menaces à la validité exposées (§6.6, p. 19).

Limites
1. Données simulées uniquement, pas de capteurs réels ni de bruit (§6.6, p. 19 ; conclusion p. 20).
2. Allocation statique des patterns, sans équilibrage, ni failover, ni gestion de données manquantes ni règles robustes au bruit (§4.3, p. 10 ; §6.6 ; p. 20).
3. Les règles sont des seuils simples (Table 3) et la comparaison quantitative exclut le seul pattern de corrélation inter-flux ; les gains mesurés (Table 8) valent pour ce déploiement précis (1 Orange Pi contre 3 nœuds) et ne se généralisent pas, comme le disent les auteurs (p. 19). Aucun taux de détection ni de faux positifs n'est mesuré (non vérifié : aucune métrique de ce type dans le texte lu).

## 5. Détails utiles à EVA-Guard

- Événements/métriques surveillés : températures uniquement (frigo, labo). Aucune métrique de nœud (pairs, connexions, bande passante, blocs, etc.) ni de blockchain n'est mentionnée.
- Détection d'anomalies : par seuils fixes sur la valeur (Table 3) ; l'article ne décrit aucun apprentissage automatique ni détection statistique d'anomalies. Il évoque seulement, en menace à la validité, que des données bruitées pourraient déclencher de fausses alertes si les seuils sont trop stricts (p. 19).
- Parallèle avec nos « indicateurs » : un pattern fog ressemble à un indicateur binaire produit à partir d'un flux (seuil franchi), publié comme événement complexe.
- Parallèle avec notre règle de confirmation : la couche cloud combine des événements complexes de domaines différents (FireAlert = frigo haut ET labo haut, corrélés dans les deux ordres d'arrivée, p. 14). C'est une forme de confirmation multi-sources (deux sources/domaines). L'article ne parle ni de « k indicateurs parmi n », ni de persistance temporelle, ni de fenêtre de confirmation ; la présence de fenêtres dans EPL est mentionnée (p. 11) mais aucun usage en persistance n'est décrit. Ces éléments : non vérifié / absents.
- Événements horodatés (epoch) avec identifiant de source (p. 11) : bon modèle pour la traçabilité des preuves.
- Kafka : persistance et rejeu des flux (p. 11) utiles pour rejouer des incidents.

## 6. Réutilisation dans EVA-Guard et écarts

| Élément de l'article | Réutilisation dans EVA-Guard | Écart |
|---|---|---|
| Distinction événement simple / complexe / alerte (p. 3-4, Table 2) | Vocabulaire pour métriques brutes, indicateurs, incident confirmé | Nous opérons sur des métriques de nœud Ethereum, pas des capteurs |
| Pattern = règle à seuil (Table 3) | Modèle des indicateurs déterministes | Nos indicateurs viennent aussi de ML |
| Corrélation multi-domaines au cloud (Table 4, p. 14) | Inspiration pour exiger plusieurs sources | Nous ajoutons k indicateurs, ≥2 sources et persistance, absents de l'article |
| Horodatage + SensorId (p. 11) | Schéma de preuve traçable | Nous attachons aussi des explications |
| Kafka + Esper (p. 10-11) | Option d'implémentation de la surveillance | Choix non imposé ; poids probablement excessif pour un mini-projet (jugement de notre part) |
| Edge-fog-cloud et placement des patterns (p. 8-10) | Idée de décomposer par domaine | Mini-projet sans déploiement distribué prévu (non vérifié côté projet) |
| Latence/débit (Tables 7-8) | Références d'ordre de grandeur CEP | Non transposables : matériel et charge différents |
| Pas de ML, pas de LLM, pas de RAG | Aucune | EVA-Guard ajoute ML, LLM+RAG, confirmation explicable |

Comparaison de pipeline : article = capteurs → Kafka → CEP fog (seuils) → CEP cloud (corrélation) → alertes ; EVA-Guard = surveillance → ML → LLM+RAG → preuves multi-sources → règle de confirmation déterministe → explication. L'article couvre l'équivalent d'une couche de règles déterministes et de corrélation ; il ne couvre ni l'apprentissage, ni l'explication, ni la sécurité blockchain.

## 7. Citations (courtes)

- « DCEP is useful when event processing can be decomposed by domain » (p. 19, formulation exacte à revérifier dans le PDF).
- « each event pattern must be deployed on exactly one active CEP engine » (p. 10).
- « does not include an automatic load-balancing or scheduling algorithm » (p. 10).
- « reaches 68,027 processed events/s before saturation » (p. 1, résumé).

Remarque : citations tirées du texte extrait ; des coupures ou reformulations mineures sont possibles, à contrôler avant insertion dans le rapport.

## 8. Points incertains

- Discordance de référence : la consigne annonçait Computer Standards & Interfaces 91, 103882 (2025), sur la surveillance de blockchains ; le PDF est Computing 108:128 (2026) sur l'IoT. Il faut soit utiliser l'article réel pour ce qu'il est (CEP distribué), soit retrouver l'article blockchain attendu. Je n'ai pas vérifié l'existence de ce dernier.
- Listings 1-2 (code EPL) absents du texte extrait ; contenu des Fig. 2, 5, 6 non lisible en texte (valeurs de Fig. 5-6 non lues, seules les Tables 7-8 sont utilisées). Je n'ai pas consulté les pages du PDF en image.
- Caractéristiques du serveur, nombre de capteurs simulés, version de Kafka/Esper : non vérifié (non lus).
- Interprétation du « HospitalLabAlert » (p. 17-18) : le nom diffère de HospitalLabAirConditionerAlert (Table 2) ; correspondance supposée, non vérifiée.
- Latence distribuée non monotone (667,86 ms à 500 ev/s contre 1026,50 ms à 100 ev/s, Table 8) : non expliquée par l'article.
- Pas de détail sur la détection d'anomalies, les faux positifs ou la persistance : absents du texte.
