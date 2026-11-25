# Fiche de lecture : Rehman et al., « Eclipse Attacks in Blockchain Networks: Detection, Prevention, and Future Directions »

Convention de pagination : « p. 259xx » = numéro de page imprimé IEEE Access (vol. 13, 2025) ; « PDF p. N » = page du fichier PDF (16 pages, p. 25918 = PDF p. 1). Les tableaux et figures sont des images : les chiffres des Tableaux 1 à 5 ont été relus sur le rendu de la page, pas sur le texte extrait.

## 1. Référence et problème visé

**Référence réelle** : Z. Rehman, M. A. Gregory, I. Gondal, H. Dong, M. Ge, « Eclipse Attacks in Blockchain Networks: Detection, Prevention, and Future Directions », *IEEE Access*, vol. 13, pp. 25918-25933, 2025, DOI 10.1109/ACCESS.2025.3538837 (reçu le 15/01/2025, publié le 04/02/2025 ; p. 25918).

**Problème visé** : l'article décrit comment une attaque Eclipse isole un nœud en monopolisant ses connexions pair-à-pair (p. 25918, Fig. 1), quels en sont les effets (double dépense, censure, perturbation du consensus, gaspillage de ressources, fuites), et passe en revue les méthodes de détection et de prévention ainsi que leurs limites (Résumé, p. 25918 ; contributions listées p. 25919).

**Nature de l'article : survey (article de synthèse) qualitatif.** L'introduction le dit elle-même : « This survey provides a comprehensive overview… » (p. 25918). Il ne propose ni méthode nouvelle, ni protocole expérimental, ni jeu de données, ni code. Voir §3.

**Point à corriger dans le cahier des charges** : la référence « Rehman et al. 2026, J. Network and Computer Applications 246, 104416, détection robuste d'Eclipse Attack » ne correspond pas à ce PDF. Le document est paru dans IEEE Access en 2025 et c'est une synthèse, pas une méthode de détection « robuste » évaluée. (Nous n'avons pas vérifié si un autre article de ces auteurs existe dans J. Netw. Comput. Appl. : non vérifié.) La bibliographie de l'article ne contient aucune référence à « 104416 » ; la seule entrée de J. Netw. Comput. Appl. est [57] (vol. 215, 2023, art. 103633, sur la blockchain pour la santé, p. 25932).

## 2. Contenu et architecture

### Plan (p. 25919)
II. Travaux connexes ; III. Fonctionnement des attaques Eclipse ; IV. Impact ; V. Détection et prévention ; VI. Défis ; VII. Pistes futures ; VIII. Conclusion (le plan annoncé p. 25919 parle de « Section VII » pour la conclusion, alors que le corps du texte numérote « VIII » p. 25931 : petite incohérence interne).

### Taxonomie centrale : Fig. 2 (p. 25920, PDF p. 3)
Schéma en arbre, trois branches issues de « Eclipse Attacks » :
- **Attack Types** : Node Discovery Manipulation ; Network Partitioning ; Information Flow Exploitation.
- **Detection Methods** : Consensus Verification ; Peer List Auditing ; Network Monitoring.
- **Prevention Strategies** : Network Diversity ; Cryptographic Authentication.

Remarque : le texte de la Section V.B (p. 25927-25928) détaille trois mesures préventives (« Harden Peer Discovery », « Foster Network Diversity », « Set Boundaries » avec limitation de débit), donc plus que les deux feuilles de la Fig. 2 ; la Section VII ajoute encore des solutions à court et long terme.

### Figure principale de déroulement : Fig. 3 (p. 25921, PDF p. 4)
Diagramme de séquence à quatre acteurs (Attacker, Victim Node, Honest Nodes, Blockchain Network). Lecture entrée → traitement → sortie :
1. Entrée : l'attaquant « spoof or overwhelm discovery » sur la victime ; la victime se déconnecte des nœuds honnêtes et se connecte aux nœuds malveillants.
2. Traitement : l'attaquant contrôle le flux d'information ; la victime relaie ses transactions via l'attaquant ; boucle « pour chaque transaction » : filtrage ou altération.
3. Maintien : l'attaquant maintient le contrôle ; la victime tente de se reconnecter aux nœuds honnêtes et reçoit un rejet « due to attack » ; la victime reste isolée.
4. Sortie : bloc parallèle « Adjust attacks to new defenses » → « Still compromised ».

### Quatre phases décrites en Section III (p. 25921-25924)
1. **Manipulation de la découverte de nœuds** (Fig. 4, p. 25922) : corruption de la table de pairs de la victime par des nœuds Sybil ; pour Ethereum, le texte cite le DHT Kademlia, les requêtes FIND_NODE, les réponses injectant des pairs contrôlés par l'attaquant, et l'exploitation de la politique d'éviction (pairs les moins récemment vus / moins actifs) (p. 25921-25922).
2. **Partitionnement réseau** (Fig. 5 et 6, p. 25922-25923) : isolement via le routage entre systèmes autonomes (AS1 victime, « Attacker AS », AS2/AS3 coupés) ; le texte relie cela à la double dépense (Fig. 6).
3. **Exploitation du flux d'information** (Fig. 7, p. 25923) : retenue de blocs, retard de propagation, fausses transactions ou fausse version de la chaîne.
4. **Maintien de l'attaque** (Fig. 8, p. 25924) : boucle de surveillance/adaptation (« Adjust Node Discovery », « Adapt to Network Changes », « Maintain Isolation and Control »).

Vulnérabilités exploitées (p. 25924) : empoisonnement de la table de pairs, faiblesses de protocole (vérification des nœuds et des messages), manque de redondance des connexions, fonctions d'anonymat.

### Impacts (Section IV, p. 25924-25926)
Double dépense, censure de transactions, perturbation du consensus, gaspillage de ressources, atteintes à la sécurité/vie privée.

### Détection (Section V.A, p. 25926-25927)
Trois familles : surveillance réseau (outils cités : Wireshark, Snort, parfois couplés à du ML), audit des listes de pairs (avec Merkle trees cités pour vérifier des identités), vérification du consensus par recoupement avec des sources externes (BlockScout pour Ethereum, Chainlink/oracles). Chaque famille est accompagnée de ses limites (faux positifs, coût, point de défaillance unique, latence).

### Prévention (Section V.B, p. 25927-25928) et faisabilité (V.C, Tableau 4)
Durcissement de la découverte (authentification ECDSA, sélection aléatoire), diversité réseau, limites (rate limiting, filtrage par métriques de confiance).

### Défis (Section VI, Tableau 5) et futur (Section VII, p. 25930-25931)
Long terme : identité décentralisée et réputation des pairs, cryptographie avancée (homomorphe, preuves à divulgation nulle), IA/ML, cross-chain et couche 2. Court terme : surveillance P2P, sélection aléatoire, limites dynamiques de connexions, rafraîchissement périodique des pairs, limitation de débit, correctifs rapides, bootstrapping fiable, sensibilisation.

## 3. Données et évaluation

**L'article n'a pas d'expérience propre.** Aucune implémentation, aucun jeu de données, aucun banc d'essai, aucune métrique mesurée par les auteurs ; la recherche des mots « experiment », « dataset », « simulation » dans le texte ne renvoie que des mentions de travaux cités (p. 25920 pour les simulations de [5], p. 25927-25928 pour NetEm cité comme outil, p. 25931 pour les limites des jeux de données d'entraînement ML). Les réseaux considérés sont comparés de façon qualitative : Bitcoin, Ethereum, Hyperledger, Polkadot (Tableau 2, p. 25925).

**Seuls chiffres de l'article** (Tableau 1, « Impact of eclipse attacks on key metrics », p. 25925, PDF p. 8), sans source, méthode ni référence associée dans le tableau :

| Métrique | Fonctionnement normal | Sous attaque Eclipse |
|---|---|---|
| Transaction Confirmation Time | 10s-15s | 30s-60s |
| Consensus Time | ~1 min | >3 mins |
| Double-Spend Success Rate | <0.01% | >25% |
| Resource Utilization | Optimized | 150%-200% |

Le texte introduit le Tableau 2 comme basé sur « statistical findings from the literature » (p. 25926), mais ses cases sont qualitatives (ex. Ethereum : « High delays from Kademlia DHT isolation [5] » ; double dépense « High success under Sybil conditions [5] » ; Hyperledger : « Low success via strict identity checks [12] » ; Polkadot : « Limited success from layered security [14] »).

**Tableau 4 (p. 25929, PDF p. 12), faisabilité des défenses (valeurs qualitatives)** :
- Vérification cryptographique des pairs : efficacité en ressources « Moderate », passage à l'échelle « High », adaptée aux réseaux permissionnés, défi « High computational overhead ».
- Détection d'anomalies par ML : « Moderate », « High », adaptée avec sélection optimisée de caractéristiques, défi « High initial training cost ».
- Diversité de pairs : « High », « Moderate », adaptée avec optimisation géographique, défi « May introduce latency ».
- Limitation de débit adaptative : « High », « High », adaptée aux environnements dynamiques, défi « Balancing false positives and negatives ».

**Tableau 3 (p. 25927, PDF p. 10)** : comparatif de neuf « stratégies de transfert (handover) » d'attaquant avec complexité technique, difficulté de détection, impact et contre-mesures associées, d'après des références citées. Ce sont des évaluations qualitatives (Low à Very High) de la part des auteurs, sans protocole expliqué. Tableau 5 (p. 25930) : défis de mitigation et « difficulté de mitigation », également qualitatif.

## 4. Forces et limites

**Forces**
1. **Taxonomie claire attaque / détection / prévention** (Fig. 2, p. 25920) servant de grille de lecture pour cadrer un projet : utile pour structurer la couverture d'un système de détection.
2. **Chaque méthode de détection est présentée avec ses limites concrètes** (faux positifs et coût de la surveillance réseau ; coût et fréquence des audits de pairs ; dépendance et latence de la vérification externe de consensus, p. 25926-25927) : honnêteté utile pour justifier des choix de conception.
3. **Cadrage opérationnel de la faisabilité et des défis** (Tableaux 4 et 5, Section VI, p. 25928-25930) : ressources, bande passante, passage à l'échelle, réponse automatisée, distinction permissionné/permissionless ; et mention de l'IA/ML pour la détection avec ses limites (données biaisées, attaques adverses, p. 25931).

**Limites**
1. **Aucune validation empirique** : le Tableau 1 (p. 25925) donne des chiffres nets (« >25% » de double dépense, « >3 mins » de consensus) sans source ni méthode ; ils ne peuvent pas servir de référence quantitative.
2. **Peu de spécificité Ethereum** : l'article ne mentionne que Kademlia/FIND_NODE (p. 25921-25922) et ne nomme ni discv4 ni discv5, ni limites de pairs des clients, ni les ENR ; il traite Ethereum surtout par analogie avec Bitcoin et par les travaux [5], [10], [16]. Il ne traite pas non plus le DoS P2P en tant que tel (aucune occurrence).
3. **Rigueur de citation inégale** : p. 25926, Wireshark est cité avec [44], qui est en réalité « Am I eclipsed? A smart detector of eclipse attacks for Ethereum » (p. 25932) ; le Tableau 2 attribue des résultats Polkadot à [14], qui est « Hijacking Bitcoin » (p. 25932) ; p. 25928 l'attaque 51% d'Ethereum Classic en 2019 est présentée comme « a notable example of an eclipse attack », ce qui n'est pas étayé dans le texte (non vérifié de notre côté). Les travaux pertinents pour la détection sur Ethereum ([20], [44], [50], [52]) sont en bibliographie mais leurs méthodes ne sont pas décrites.

## 5. Détails utiles à EVA-Guard (niveau conceptuel et défensif)

### Symptômes / indicateurs observables mentionnés
- **Table de pairs dominée par des entrées contrôlées par un même acteur ; pairs « apparemment » diversifiés mais en réalité liés** : faible diversité d'adresses/identifiants/segments réseau (p. 25921-25922, 25924).
- **Anomalies dans les listes de pairs** et **volumes de trafic anormaux** (p. 25926) ; métriques suggérées pour le ML : flux de trafic, latence, fréquence de connexion des pairs.
- **Retard de blocs / désynchronisation** : le nœud retombe derrière le réseau, accepte des données périmées ou une chaîne minoritaire (p. 25923-25925).
- **Divergence avec la vue externe** : blocs manquants, historique de transactions différent, hash de blocs divergents (p. 25927).
- **Échecs répétés de reconnexion à des pairs honnêtes** (Fig. 3, p. 25921) ; « sudden isolation of a node » et échanges de paquets irréguliers (p. 25931).
- **Délais de propagation de blocs, schémas de communication inhabituels** (p. 25930).
- Effets secondaires : confirmations plus lentes et ressources accrues (Tableau 1, non étayé).
- Faux positifs à garder en tête : maintenance, mises à jour réseau, changements de comportement utilisateur (p. 25926).

### Contre-mesures et méthodes de détection citées
- Surveillance réseau (Wireshark, Snort, ML sur flux/latence/fréquence de connexions) ; audit des listes de pairs (Merkle trees pour vérifier les identités) ; recoupement de consensus avec BlockScout, Chainlink ou autres oracles (p. 25926-25927).
- Prévention : authentification des messages de pairs (ECDSA) et sélection aléatoire ; diversité géographique et topologique ; limitation de débit et filtrage par confiance (p. 25927-25928).
- Court terme (p. 25931) : rafraîchissement périodique des pairs, limites de connexions dynamiques, correctifs rapides, bootstrapping depuis des sources de confiance, éducation des opérateurs.
- Long terme : identité décentralisée et réputation, cryptographie avancée, ML adaptatif (réponse : alerte ou isolement de nœuds suspects, p. 25930), cross-chain/couche 2.
- Références de bibliographie à creuser pour la détection : [20] (détection comme changement non paramétrique), [44] (détecteur pour Ethereum), [50] (extraction de caractéristiques profondes), [52] (supervision réseau Ethereum « Tikuna »), [39], [40] (détection/mitigation P2P), p. 25932 ; non lues, donc non vérifiées.

### Spécifique à Ethereum
- Découverte basée sur Kademlia DHT, requêtes FIND_NODE, réponses itératives ou récursives, table de pairs de taille limitée (p. 25921-25922).
- Politique d'éviction visant les pairs les moins récents ou actifs (p. 25922).
- Table 2 : Ethereum jugé « highly susceptible » (p. 25926) ; références [5] (attaques Eclipse à faibles ressources sur Ethereum), [10], [16] (falsification de node records).
- **Non traité** : discv4 vs discv5, structure en buckets, limites de pairs entrants/sortants par client, comportement lors des redémarrages. Ces points devront venir d'autres sources (spécifications et documentation des clients).

## 6. Réutilisation dans EVA-Guard et écarts

Réutilisable :
- Taxonomie à trois axes (attaque / détection / prévention) → squelette du chapitre d'état de l'art.
- Liste des symptômes (diversité des pairs, retard de blocs, échecs de reconnexion, divergence externe) → base des features de surveillance et des signaux du moteur de règles.
- Vérification de consensus par sources externes (BlockScout, oracles) → modèle des « preuves multi-sources », avec la réserve de l'article (point de défaillance unique, latence, p. 25927).
- Audit des listes de pairs → indicateur « diversité de table de pairs ».
- Limites énoncées du ML (faux positifs, données biaisées, attaques adverses, p. 25931) → justification de ne pas laisser le ML seul décider et de passer par une confirmation.
- Réponse automatisée « adaptative et discernante » (p. 25930) → motive la règle de confirmation avant action.

Écarts :
- **Aucun chiffre de performance exploitable** : pas de référence quantitative pour comparer EVA-Guard ; nos mesures devront venir de nos propres expériences.
- **DoS P2P absent** de l'article : à sourcer ailleurs.
- **Pas de détails Ethereum modernes** (discv4/discv5, limites de pairs) : à compléter.
- **Pas de LLM ni de RAG** : l'article ne parle que d'IA/ML générique et d'un modèle fondation distribué ([15], p. 25920) ; la couche LLM + RAG et l'explication sont des apports propres d'EVA-Guard.
- **Pas de règle de confirmation formalisée** : l'article mentionne seulement la vérification de consensus et la possibilité d'actions automatiques.

### Comparaison avec le pipeline EVA-Guard
| Étage EVA-Guard | Correspondance dans l'article |
|---|---|
| Surveillance | Surveillance réseau + audit de pairs (V.A, p. 25926) : correspondance partielle, sans métriques précises |
| ML | Mentionné de façon générique (V.A, VII.A.3) : sans modèle ni données |
| LLM + RAG | Absent |
| Preuves multi-sources | Proche de « Verification of Consensus » (p. 25927), qui s'appuie sur BlockScout, oracles, autres nœuds |
| Règle de confirmation | Absente, seulement l'idée de réponse automatisée adaptative (p. 25930) |
| Explication | Absente |

## 7. Citations (courtes, ≤ 15 mots)

1. « monopolize the connections to a target node » (Résumé, p. 25918, définition d'une attaque Eclipse)
2. « Eclipse attack detection requires adoption of several different approaches. » (p. 25926)
3. « The limitation of network monitoring is the potential for false positives. » (p. 25926)
4. « a potential single point of failure » (p. 25927, à propos des sources externes de vérification du consensus)
5. « AI/ML-based systems are inherently dependent on the quality and diversity of training data. » (p. 25931)

## 8. Points incertains

- Existence éventuelle d'un autre article de Rehman et al. dans J. Netw. Comput. Appl. 246 (2026) correspondant à la référence du cahier des charges : non vérifié (hors du PDF fourni).
- Origine et méthode des chiffres du Tableau 1 : non précisées dans l'article ; non vérifiable.
- Contenu des références [5], [10], [16], [20], [44], [50], [52] : non lu, nous ne faisons que relayer ce que l'article en dit.
- Exactitude de l'affirmation sur Ethereum Classic 2019 (p. 25928) : non vérifiée.
- Les Fig. 1, 5, 6, 7 ont été décrites d'après le texte et l'aperçu ; seuls les Fig. 2, 3, 8 et les Tableaux 1 à 5 ont été relus en image.
- Paramètres Ethereum (discv4/discv5, limites de pairs, taille des buckets) : absents de l'article, non vérifiés.
- La Fig. 2 et la Section V ne se recouvrent pas exactement (deux feuilles de prévention contre trois mesures détaillées) : interprétation à confirmer par les étudiants.
