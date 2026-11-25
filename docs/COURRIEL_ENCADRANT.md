Objet : Mini-projet Blockchain EVA-Guard — traces d'attaque et validation de l'évaluation

Bonjour Madame / Monsieur,

Nous avons réalisé un prototype d'EVA-Guard (détection ML, hypothèse LLM + RAG, preuves multi-sources, confirmation déterministe, dashboard) et un rapport. Résultats actuels :
- sur télémétrie simulée : le contexte LLM/RAG réduit les fausses alertes, la confirmation multi-sources n'apporte pas de gain supplémentaire ;
- sur traces réelles de comportement normal et bénin (nœud Geth, redémarrages, rafales de transactions légitimes) : aucune fausse alerte, mais nous ne pouvons pas mesurer le rappel faute de traces d'attaque.

Pour conclure, nous aurions besoin de votre avis sur trois points :
1. Pouvez-vous nous fournir des traces ou un jeu de données autorisés d'attaques Eclipse et DoS P2P sur Ethereum (ou nous indiquer une source publique) ?
2. À défaut, existe-t-il un environnement isolé et une méthode que vous validez pour produire ces épisodes sous votre supervision ? Nous n'en exécuterons aucun sans votre accord écrit.
3. Si aucune trace n'est disponible, acceptez-vous que le rappel soit présenté uniquement sur données simulées, avec les limites explicitées dans le rapport ?

Nous pouvons vous envoyer le rapport (20 pages) et lancer une démonstration quand vous le souhaitez.

Cordialement,
Mohamed Amine Gharbi, Baya Sayah, Hadil Kharoubi, Hedi Gouia
