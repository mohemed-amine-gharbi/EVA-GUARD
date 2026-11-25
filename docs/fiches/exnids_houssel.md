# Fiche de lecture : eX-NIDS (Houssel et al.)

Source lue : texte intégral extrait du PDF (15 p.). Les numéros de page sont ceux imprimés sur le PDF (le texte est la version preprint arXiv, voir section 8). Les passages marqués « notre analyse » sont des commentaires de l'équipe EVA-Guard, pas des affirmations de l'article.

## 1. Référence exacte et problème visé

**Référence telle qu'elle figure sur la première page du PDF** : Paul R. B. Houssel, Siamak Layeghy, Priyanka Singh, Marius Portmann (School of ITEE, University of Queensland, Brisbane), « eX-NIDS: A Framework for Explainable Network Intrusion Detection Leveraging Large Language Models », arXiv:2507.16241v1 [cs.CR], 22 juillet 2025 ; mention « Preprint submitted to Elsevier, September 15, 2025 » (p. 1).

**Correction par rapport à la référence attendue** : le PDF fourni ne porte ni la revue « Computers & Electrical Engineering 129, 110826 » ni l'année 2026. La première page indique un preprint arXiv de 2025. La référence revue/volume/article n'est donc **pas vérifiée** par ce document (voir section 8).

**Problème visé** (p. 1-2) : les NIDS à base de ML détectent bien mais n'expliquent pas leurs alertes ; les méthodes XAI classiques (SHAP) demandent une expertise ML, ne reposent que sur des anomalies statistiques et n'intègrent pas de connaissance externe. Les auteurs proposent d'utiliser un LLM non pas pour détecter, mais pour expliquer en langage naturel pourquoi un flux déjà classé malveillant l'a été, en enrichissant le prompt de contexte et de CTI.

## 2. Architecture du framework

Deux frameworks sont décrits (Section 3, p. 4-9).

**Baseline : Basic-Prompt Explainer (Fig. 1, p. 4 ; prompt en Fig. 2, p. 5)**
- Entrée : trafic réseau converti en enregistrements NetFlow, classés malveillant/bénin par un NIDS ML existant (Section 3.1, p. 4).
- Traitement : seuls les flux malveillants passent au « Prompt Aggregator », qui insère le NetFlow dans un gabarit contenant une instruction (demande d'expliquer en citant des valeurs de features précises).
- Sortie : explication en langage naturel destinée à l'opérateur réseau (Fig. 1).

**eX-NIDS : Augmented-Prompt Explainer (Fig. 4, p. 7)**
Même chaîne, avec en plus un module **Prompt Augmenter** qui produit une « Context Specific Information » ajoutée au prompt (« Augmented Prompt ») avant le LLM.

**Prompt Augmenter (Fig. 5, p. 7 ; texte p. 7-9)** : à partir du NetFlow malveillant, trois extracteurs/sources :
1. *Spécification NetFlow* : paires nom de feature / définition (en-têtes, FlowSet, champs de flux), pour éviter les erreurs sur le sens et les unités (p. 7).
2. *Connaissance liée aux IP* : un extracteur d'adresses IP alimente trois sources : **IP Threat Intelligence** (une chaîne de texte par IP), **IP Geo-Localisation** (ville, pays...), **IP History** (flux malveillants précédents liés à la même IP, issus d'une base de données interne) (Fig. 5 ; p. 8).
3. *Identifiants de protocole* : extracteurs L7 (L7_PROTO) et L4 (PROTOCOL) puis « Protocol ID to Name Mapper » (ex. ID 17 = UDP) (p. 8-9).
Un bloc « Combine Text » assemble le tout. La légende de la Fig. 5 précise que les connexions aux ressources externes et à la base interne ne sont pas représentées.

**Ce qu'est la « CTI » ici** : dans l'article, c'est la donnée de threat intelligence **par adresse IP** (réputation/activité connue, par ex. « SSH brute-force » dans l'exemple de la Fig. 7, p. 9), plus l'historique des flux et la géolocalisation. La source précise de la CTI n'est pas nommée dans le texte (non vérifié).

**Construction du prompt (Fig. 6, p. 8)** : le contexte est **ajouté à la fin** du prompt du baseline (instruction + échantillon NetFlow), en trois rubriques : « NetFlow Specification », « Protocol Specific Knowledge », « IP Specific Knowledge » (p. 9). Le texte complet de l'exemple n'est pas reproduit dans l'article (« space constraints », p. 9).

**LLM** : Llama3-70B-Instruct (inférence locale) et GPT-4, modèle `gpt-4-1106-preview` via l'API OpenAI (Section 4.2, p. 11). Température 0,7, max 2048 tokens.

**Sortie** : texte libre, liste d'arguments citant des valeurs de features, avec conclusion (exemple GPT-4 en Fig. 7, p. 9, à comparer à la Fig. 3, p. 6). Pas de format structuré imposé (non vérifié au-delà de l'instruction de la Fig. 2).

**RAG** : l'article dit explicitement ne pas en utiliser (p. 9-10) : les attributs NetFlow sont structurés, une base classique suffit, sans embeddings.

## 3. Données et évaluation

- **Jeu de données** : NF-CSE-CIC-IDS2018-v2 [26] ; **50 flux malveillants** échantillonnés « equally » (Section 4, p. 10). Seuls les flux malveillants sont évalués.
- **LLM comparés** : Llama3-70B-Instruct et GPT-4 (gpt-4-1106-preview), chacun en Basic Prompt vs eX-NIDS (p. 11-12).
- **Évaluation** : inspection **manuelle par deux experts du domaine** selon trois métriques définies par les auteurs (Section 4.1, p. 10-11), évaluées indépendamment l'une de l'autre :
  - *Explanation Correctness* : validité sémantique ; une explication n'est correcte que si **tous** ses arguments le sont.
  - *Feature Consistency* : usage correct des valeurs et définitions de features (ex. débit en bps et non Bps).
  - *Factual Consistency* : absence d'informations fabriquées ou mal calculées (ex. 4294964 ms confondu avec 43 min au lieu de 71 min).

**Table 1 (p. 12), valeurs recopiées** (moyenne ± valeur entre parenthèses telle qu'imprimée) :

| Modèle | Méthode | Correctness (%) | Feature Cons. (%) | Factual Cons. (%) | Moy. (%) |
|---|---|---|---|---|---|
| Llama3 70B-Instruct | Basic Prompt | 26 (±06) | 84 (±05) | 42 (±07) | 50.66 |
| Llama3 70B-Instruct | eX-NIDS | 36 (±06) | 100 (±0) | 90 (±04) | 75.33 |
| GPT-4 | Basic Prompt | 40 (±06) | 96 (±02) | 78 (±05) | 71.33 |
| GPT-4 | eX-NIDS | 80 (±05) | 100 (±0) | 92 (±03) | 90.66 |

**Coût et latence (p. 12)** : Llama3 local, 100 itérations : 4 s en moyenne (basic) contre 6 s (augmenté). Prompts moyens : 1 244 caractères / 461 tokens (basic) contre 6 685 caractères / 2 308 tokens (augmenté). Coût estimé pour 1 000 requêtes via l'API : 5,75 $ (basic) contre 10,37 $ (augmenté).

**Conclusion chiffrée (p. 13)** : avec GPT-4 + eX-NIDS, 80 % d'explications correctes, 92 % factuellement cohérentes, 100 % référençant correctement les valeurs du NetFlow.

## 4. Forces et limites

**Forces**
1. **L'enrichissement du prompt améliore les trois métriques pour les deux modèles** (Table 1, p. 12) : par ex. correctness de GPT-4 de 40 à 80 %, factual consistency de Llama3 de 42 à 90 %.
2. **Le contexte cible des causes de hallucination identifiées** : spécification des features, IDs de protocole, IP/CTI (p. 7-8) ; l'exemple qualitatif montre des unités et valeurs correctes (Fig. 7 vs Fig. 3, p. 6 et 9).
3. **Évaluation explicite de la correction, et pas seulement de la lisibilité** : critiques adressées à Ziems et al. dans la section 2 (p. 4), métriques définies avec exemples (p. 10-11) ; code d'évaluation publié (note 2, p. 11).

**Limites**
1. **Hallucinations et erreurs de raisonnement persistent** : la correctness reste la métrique la plus faible (36 % pour Llama3 avec eX-NIDS), attribuée au manque de raisonnement des modèles en réseau ; Llama3 se trompe encore sur des conversions ms/s et n'exploite pas les 5 connexions précédentes (Section 5, p. 12). Les auteurs écrivent aussi que des travaux supplémentaires sont nécessaires avant usage critique (p. 13).
2. **Évaluation de petite taille et subjective** : 50 flux, un seul jeu de données, deux évaluateurs manuels (p. 10-11). L'accord inter-évaluateurs et la signification des ± ne sont pas précisés (non vérifié). Les auteurs reconnaissent qu'une étude utilisateurs auprès d'opérateurs reste à faire (p. 13).
3. **Pas de confirmation indépendante de l'alerte** : le framework explique la décision d'un NIDS en amont, sur des flux déjà classés malveillants ; seule la partie malveillante est évaluée (p. 10) ; l'article ne mesure ni faux positifs expliqués ni vérification croisée de l'explication par une source indépendante. Notre analyse (l'article ne l'affirme pas), cohérente avec le fait que les auteurs jugent les LLM peu adaptés à la détection (p. 2, 4). À noter aussi la dépendance au prompt et au modèle : écart d'environ 20 points entre GPT-4 et Llama3 (p. 12), et prompt 5 fois plus long avec coût accru (p. 12) ; l'article ne teste pas de variantes de formulation du prompt (non vérifié, notre analyse).

## 5. Détails utiles à EVA-Guard

- **Contexte du prompt** : instruction + échantillon brut + 3 rubriques de contexte (spécification des champs, noms de protocoles, connaissances par IP incluant historique des flux) ajoutées en fin de prompt (Fig. 6, p. 8-9). La consigne impose de citer des valeurs de features présentes dans l'échantillon (Fig. 2, p. 5).
- **Usage de la CTI et équivalent de notre RAG** : lookup déterministe en base (IP, historique, géolocalisation, mapping d'IDs), pas de recherche vectorielle ; l'article justifie ce choix par la nature structurée des données (p. 9-10). Notre RAG sur fiches de diagnostic recouvre un besoin différent (texte non structuré) ; pour des champs structurés (types de messages P2P, ports, ID de pairs), un lookup direct est le parallèle le plus proche.
- **Hallucinations** : typologie de trois erreurs observées sans contexte (p. 5-6) : (a) hallucinations de valeurs absentes ou différentes de l'entrée, (b) références incohérentes aux features, (c) mauvaises interprétations de valeurs (ex. port éphémère jugé « inhabituel »). Traitement proposé : uniquement la réduction par contexte ; aucun mécanisme de vérification automatique des sorties n'est décrit (non vérifié au-delà du texte lu).
- **Format de sortie** : texte libre en liste d'indicateurs avec valeurs citées, puis synthèse (Fig. 7, p. 9). Pas de schéma JSON ni de score de confiance décrits.
- **Mesure de qualité réutilisable** : trois métriques binaires par explication (correction, cohérence des features, cohérence factuelle) évaluées indépendamment (p. 10-11).

## 6. Réutilisation dans EVA-Guard et écarts

| Élément | Dans eX-NIDS | Dans EVA-Guard |
|---|---|---|
| Déclencheur | Flux NetFlow classé malveillant par un NIDS ML | Alerte du module ML sur des signaux de nœuds Ethereum (Eclipse, DoS P2P) |
| Rôle du LLM | Explication seulement ; détection hors LLM (p. 4) | Idem pour l'explication, plus rôle agentique de diagnostic |
| Enrichissement | Specs NetFlow, protocoles, IP/CTI, historique (Fig. 5) | Fiches de diagnostic via RAG + preuves multi-sources (ajout) |
| Récupération | Base classique, pas de RAG (p. 9-10) | RAG sur fiches ; lookups déterministes possibles pour champs structurés |
| Confirmation | Aucune : l'explication n'est pas confirmée indépendamment | Règle de confirmation déterministe multi-sources (ajout) |
| Cible | Réseau IP classique, NF-CSE-CIC-IDS2018-v2 | Nœuds Ethereum (couche P2P) |
| Sortie | Texte libre | Explication adossée aux preuves ; format à définir par nous |
| Évaluation | 50 flux, 2 experts, 3 métriques (p. 10) | Reprendre les métriques de correction/cohérence factuelle (idée) |

**Comparaison avec notre pipeline** (surveillance → ML → LLM+RAG → preuves multi-sources → règle de confirmation → explication) : eX-NIDS couvre les étapes « ML en amont → contexte → LLM → explication ». Il n'a ni preuves multi-sources ni règle de confirmation ; EVA-Guard ajoute cette confirmation déterministe (la décision ne repose pas sur la sortie du LLM) et cible Ethereum. Notre analyse : l'article montre que la sortie du LLM, même enrichie, peut rester incorrecte (p. 12), ce qui motive de ne pas lui déléguer la confirmation.

## 7. Citations clés (≤ 15 mots)

- « Retrieval Augmented Generation (RAG) [25] is not considered necessary in this context » (p. 9)
- « An explanation is correct only if all provided arguments are correct. » (p. 10)
- « The LLM explanation layer introduces a notable performance overhead » (p. 12)
- « leads to frequent hallucinations and misinterpretations » (p. 13)
- « needed before they can be fully relied upon in critical security contexts » (p. 13)

## 8. Points incertains

- **Référence de revue non vérifiée** : le PDF est un preprint arXiv v1 (22 juillet 2025, « submitted to Elsevier » le 15 septembre 2025). « Computers & Electrical Engineering 129, 110826 » et l'année 2026 ne figurent pas dans le document ; à confirmer sur la page éditeur avant de citer (la version publiée peut différer du preprint).
- **Incohérences internes de l'article** : le texte (p. 12) annonce un gain de factual consistency de « 38 % » pour Llama3 alors que la Table 1 donne 42 → 90, soit +48 points ; « GPT-4 20 % plus haut que Llama3 » correspond à l'écart en méthode basique (71,33 vs 50,66) mais l'écart avec eX-NIDS est d'environ 15 points (90,66 vs 75,33). L'amélioration « over 20 % » du résumé : +24,7 points en moyenne pour Llama3, +19,3 pour GPT-4 d'après la Table 1 (calcul de notre part).
- Signification des valeurs « ± » de la Table 1 : non précisée.
- Source exacte de la CTI et des données de géolocalisation : non nommée dans le texte ; la base interne et les ressources externes ne sont pas détaillées (Fig. 5).
- Mode d'échantillonnage « equally » des 50 flux (par classe d'attaque ?) : non vérifié.
- Accord entre les deux évaluateurs : non indiqué.
- Aucune figure n'a été consultée visuellement dans le PDF ; les descriptions des Fig. 1 à 7 reposent sur le texte extrait (étiquettes des blocs lisibles dans l'extraction).
- Le dépôt de code cité (note 2, p. 11) n'a pas été consulté.
