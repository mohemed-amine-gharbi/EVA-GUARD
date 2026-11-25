"""Rapport TECHNIQUE : comment fonctionne EVA-Guard (architecture, modèles IA, RAG et sa base de connaissances, confirmation, évaluation).

    python report/make_diagrams.py && python report/build_tech_report.py   ->   report/EVA-Guard_Rapport_Technique.pdf
Les chiffres sont lus dans results/ ; les seuils et paramètres sont lus dans le code (eva_guard/).
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Spacer, Preformatted
from reportlab.platypus.tableofcontents import TableOfContents

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as br                       # noqa: E402  (styles, helpers, polices)
from build_report import P, bullets, table, img, n, S, ROOT, RES, FIG   # noqa: E402

OUT = ROOT / "report" / "EVA-Guard_Rapport_Technique.pdf"
sys.path.insert(0, str(ROOT))
from eva_guard import config, rag, llm                       # noqa: E402
from eva_guard.agents import Rule                            # noqa: E402


class TDoc(br.Doc):
    def __init__(self, path):
        super().__init__(path)
        self.title = "EVA-Guard — Rapport technique"


def code(text):
    return Preformatted(text, S["code"], maxLineLength=100)


def main():
    summ = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    abl = {a["system"]: a for a in json.loads((RES / "ablation_summary.json").read_text(encoding="utf-8"))}
    params = pd.read_csv(RES / "selected_params.csv")
    B1, B2, EV = summ
    ragev = json.loads((RES / "rag_eval.json").read_text(encoding="utf-8")) if (RES / "rag_eval.json").exists() else None
    sens = pd.read_csv(RES / "sensitivity.csv") if (RES / "sensitivity.csv").exists() else None
    docs = rag.load_docs()
    story = []

    # ------------------------------------------------------------------ couverture
    story += [Spacer(1, 4.5 * cm), P("EVA-Guard", "title"), Spacer(1, .4 * cm), P("Rapport technique", "sub"), Spacer(1, .5 * cm),
              P("Architecture, modèles d'IA, RAG et données du RAG,<br/>confirmation, évaluation et exploitation", "sub"), Spacer(1, 1.6 * cm),
              P("Équipe : Mohamed Amine Gharbi — Baya Sayah — Hadil Kharoubi — Hedi Gouia<br/>Encadrant : " + br.ENCADRANT, "sub"), Spacer(1, 1.6 * cm),
              P(f"Version du {date.today().strftime('%d/%m/%Y')}", "sub"), Spacer(1, 2 * cm),
              P("<b>À qui s'adresse ce document.</b> À toute personne qui doit comprendre, reproduire ou faire évoluer EVA-Guard sans lire tout le code : "
                "chaque composant est décrit avec son entrée, sa sortie, ses paramètres et la raison de ses choix. "
                "Les valeurs numériques viennent du code et des fichiers de résultats ; les limites sont indiquées là où elles s'appliquent.", "box"), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t1", fontName="DV-B", fontSize=9.5, leading=14, leftIndent=0),
                       ParagraphStyle("t2", fontName="DV", fontSize=8.5, leading=12, leftIndent=14)]
    story += [P("Table des matières", "toch"), toc, PageBreak()]

    # ------------------------------------------------------------------ 1. vue d'ensemble
    story += [P("1. Vue d'ensemble", "h1"),
              P("EVA-Guard surveille un nœud Ethereum et décide, pour chaque anomalie, si elle correspond à une <b>attaque réseau</b> (Eclipse ou déni de service P2P) "
                "ou à un événement <b>légitime</b> (redémarrage, rafale de transactions, maintenance). L'idée centrale : un modèle de ML ou un LLM peut se tromper ; "
                "on les utilise pour <i>proposer</i> une hypothèse, et une règle déterministe fondée sur des mesures indépendantes <i>décide</i>."),
              img("architecture.png", 16.8, "Figure 1 — Chaîne de traitement : observation → détection ML → hypothèse LLM + RAG → corrélation → confirmation → restitution."),
              table([["Étape", "Agent / module", "Entrée", "Sortie", "Fichier"],
                     ["Observation", "Collecteur ou simulateur", "Nœud (RPC, métriques, système)", "Une ligne de 12 métriques toutes les 10 s", "collectors/collector.py, eva_guard/simulator.py"],
                     ["Détection", "Detector", "Fenêtres lissées", "Alerte {t, score, type suspecté, métriques déviantes}", "eva_guard/detector.py"],
                     ["Interprétation", "OfflineInterpreter / MistralInterpreter", "Texte de symptômes + fiches RAG", "Hypothèse {attaque, confiance, justification, fiches citées}", "eva_guard/llm.py, rag.py"],
                     ["Corrélation", "CorrelationAgent", "Hypothèse + fenêtre", "Liste de preuves (indicateur, source, valeur, seuil, passé ou non)", "eva_guard/agents.py"],
                     ["Confirmation", "ConfirmationAgent", "Preuves successives", "Décision CONFIRMED / NOT_CONFIRMED + raison", "eva_guard/agents.py"],
                     ["Restitution", "ReportAgent, dashboard", "Alerte, hypothèse, décision", "Rapport lisible + recommandation", "eva_guard/agents.py, dashboard/app.py"]],
                    [2.5 * cm, 3.1 * cm, 3.3 * cm, 4.3 * cm, 3.7 * cm]),
              Spacer(1, 4),
              P("<b>Trois systèmes sont comparés</b> sur les mêmes données : <b>Baseline 1</b> (ML seul : toute alerte est une attaque), <b>Baseline 2</b> (ML + LLM/RAG : l'hypothèse du LLM décide) "
                "et <b>EVA-Guard</b> (ML + LLM/RAG + corrélation + confirmation déterministe). Le mode est un paramètre de <i>EvaGuard</i> : <i>ml_only</i>, <i>ml_llm</i>, <i>eva</i>.")]

    # ------------------------------------------------------------------ 2. données
    desc_rows = [["Métrique", "Source", "Signification", "Collecte réelle"]]
    real = {"peer_count": "RPC net_peerCount", "peer_churn": "taille de la différence symétrique des ensembles de pairs (admin_peers) entre deux relevés", "peer_diversity": "sous-réseaux /16 distincts parmi admin_peers",
            "single_source_ratio": "non collectable par RPC (journaux Geth requis) — retirée du modèle", "msgs_in": "compteur Prometheus p2p_ingress_eth_66_0x02 (nom supposé : vide sur notre nœud)",
            "bytes_in": "compteur Prometheus p2p_ingress (débit calculé, en ko/s)", "cpu": "psutil (processus) ou docker stats (conteneur)", "mem": "psutil (processus) ou docker stats (conteneur)", "net_io": "dérivée de bytes_in (× 0,008) : pas indépendante de bytes_in",
            "rpc_latency": "durée d'une requête RPC de sonde", "rpc_error": "échecs/timeouts des sondes RPC", "sync_lag": "eth_syncing (hauteur courante vs plus haute)"}
    for f, d in config.DESCRIPTION.items():
        desc_rows.append([f, config.SOURCE[f], d, real[f]])
    story += [P("2. Données", "h1"),
              P("2.1 Les 12 métriques et leurs trois sources", "h2"),
              P("Chaque <b>fenêtre</b> dure 10 s et produit un vecteur de 12 métriques issues de <b>trois sources indépendantes</b> : le réseau P2P, le système et l'interface RPC. "
                "Cette séparation est essentielle : la confirmation exige des preuves de plusieurs sources pour ne pas dépendre d'un seul signal."),
              table(desc_rows, [3.5 * cm, 1.6 * cm, 5.1 * cm, 6.7 * cm]), Spacer(1, 6),
              P("2.2 Prétraitement", "h2"),
              *bullets([f"<b>Lissage causal</b> : moyenne glissante sur {config.SMOOTH} fenêtres (le passé uniquement), pour réduire le bruit sans jamais utiliser le futur.",
                        "<b>Baseline</b> (<i>BaselineStats</i>) : moyenne et écart-type de chaque métrique sur les fenêtres <i>normales</i> d'entraînement ; quantiles 1 % et 99 % qui donnent les seuils des indicateurs.",
                        "<b>Normalisation</b> : z-score = (valeur − moyenne) / écart-type, utilisé par les deux modèles de ML et par le texte de symptômes.",
                        "<b>Trous de collecte</b> : interpolation linéaire (<i>real_loader.py</i>) ; une colonne entièrement vide est retirée du modèle (<i>EVA_DROP_FEATURES</i> ou détection automatique)."]),
              P("2.3 Données simulées", "h2"),
              P("Le simulateur (<i>eva_guard/simulator.py</i>) génère uniquement des <b>séries de métriques</b> (aucun trafic). Chaque run dure 100 fenêtres ; un bruit autorégressif et un niveau de charge propre au run "
                "(0,7 / 1,0 / 1,4) donnent des comportements normaux variés. Un épisode de type <i>eclipse</i>, <i>dos_p2p</i>, <i>benign_restart</i>, <i>benign_burst</i> ou <i>benign_maintenance</i> modifie "
                "ensuite les métriques selon un profil écrit à partir des symptômes décrits dans le cahier des charges. Le paramètre <i>intensity</i> (0 à 1) règle l'amplitude des épisodes offensifs."),
              table([["Jeu", "Normal", "Eclipse", "DoS P2P", "Redémarrage", "Rafale", "Maintenance"],
                     ["Entraînement", "30", "20", "20", "—", "—", "—"], ["Validation", "10", "10", "10", "8", "8", "—"],
                     ["Test", "25", "30", "30", "15", "15", "15 (jamais vue)"]], [3.2 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.6 * cm, 2.0 * cm, 3.2 * cm]),
              Spacer(1, 4),
              P("La <b>maintenance</b> n'existe qu'en test : c'est un événement légitime que les modèles n'ont jamais vu, destiné à mesurer la robustesse face à une nouveauté. "
                "Cinq graines (100 à 104) génèrent cinq jeux indépendants ; les profils sont écrits par les auteurs, d'où un risque d'optimisme (section 9).", "box"),
              P("2.4 Données réelles", "h2"),
              P("Le collecteur (<i>collectors/collector.py</i>) lit en lecture seule le RPC, les métriques Prometheus et les statistiques du processus ou du conteneur. "
                "<i>tools/run_session.py</i> enregistre des runs étiquetés (repos, charge modérée, charge élevée, redémarrage, rafale légitime) à l'aide de <i>tools/load_gen.py</i> "
                "(transferts d'ether de très faible valeur entre comptes de test). Les runs forment <i>results/runs/manifest.csv</i> (colonnes <i>run_id, file, run_type, onset, event_end</i>) ; "
                "<i>real_check.py</i> en mesure les fausses alertes. Aucune attaque n'est exécutée par ces outils.")]

    # ------------------------------------------------------------------ 3. modèles IA
    story += [P("3. Modèles d'IA de détection", "h1"),
              P("La détection combine deux modèles <i>scikit-learn</i> complémentaires, appris sur les z-scores des 12 métriques. Aucun des deux ne décide d'une attaque : ils produisent une alerte et un type <i>suspecté</i>."),
              P("3.1 Isolation Forest — « quelque chose change »", "h2"),
              *bullets(["<b>Principe</b> : isole les points en coupant l'espace au hasard ; un point anormal est isolé en peu de coupes. Le score d'anomalie est l'opposé de <i>score_samples</i> (plus grand = plus anormal).",
                        "<b>Entraînement</b> : uniquement sur les fenêtres de runs <b>normaux</b> (apprentissage non supervisé du comportement de référence). 200 arbres, graine fixée.",
                        f"<b>Seuil d'alerte</b> : choisi sur le jeu de <i>validation</i> en maximisant le F1 de la Baseline 1, parmi 40 quantiles des scores (de 70 % à 99,9 %). Valeurs obtenues : {', '.join(f'{x:.2f}' for x in params.threshold)} (une par graine).",
                        f"<b>Règle d'alerte</b> : le score doit dépasser le seuil pendant <b>{config.ALERT_CONSEC} fenêtres consécutives</b> ; la première de ces fenêtres est la fenêtre d'alerte.",
                        "<b>Pourquoi ce modèle</b> : il n'a pas besoin d'exemples d'attaques, ce qui est réaliste (les attaques sont rares et mal étiquetées) et il détecte des comportements jamais vus."]),
              P("3.2 Random Forest — « à quoi cela ressemble »", "h2"),
              *bullets(["<b>Principe</b> : 200 arbres de décision qui votent. Il apprend à distinguer <i>normal</i>, <i>eclipse</i> et <i>dos_p2p</i> à partir des fenêtres étiquetées de l'entraînement (fenêtres de l'épisode = type d'attaque, les autres = normal).",
                        "<b>Rôle</b> : fournir un <b>type suspecté</b> (<i>suspected_type</i>) à l'alerte, en moyennant les probabilités sur les fenêtres t−1 et t ; seul le meilleur type d'attaque est retenu. Il oriente l'explication et la Baseline 1.",
                        "<b>Limite</b> : il n'a vu en entraînement que des attaques et le comportement normal ; il ne connaît pas les événements bénins, ce qui explique en partie les fausses alertes de la Baseline 1."]),
              img("importance.png", 12.5, "Figure 2 — Importance des métriques pour la classification du type (Random Forest)."),
              P("3.3 Pourquoi deux modèles et pas un LLM seul", "h2"),
              P("Le ML est rapide, reproductible et mesurable ; le LLM est utile pour raisonner sur le contexte, mais il peut halluciner (l'article eX-NIDS mesure une correction de 36 % à 80 % selon le modèle, section 3 du rapport principal). "
                "L'architecture donne donc au ML la détection, au LLM l'explication, et à une règle déterministe la décision."),
              P("3.4 Limites des modèles", "h2"),
              *bullets(["Entraînés sur des profils <b>simulés</b> : sur un vrai nœud, les niveaux de base diffèrent ; il faut ré-apprendre la baseline sur vos propres runs normaux (<i>real_check</i>, dashboard).",
                        "Une seule alerte et un seul épisode par run ; pas de dérive lente de la baseline prise en compte.",
                        "Le seuil dépend du jeu de validation : sur de nouvelles données, le recalibrer."])]

    # ------------------------------------------------------------------ 4. RAG
    story += [P("4. LLM et RAG", "h1"),
              P("4.1 Le principe", "h2"),
              P("<b>RAG</b> (<i>Retrieval-Augmented Generation</i>) : au lieu de demander au LLM de répondre de mémoire, on lui fournit d'abord des <b>fiches de référence</b> pertinentes, récupérées par similarité avec les symptômes observés. "
                "L'hypothèse est ainsi adossée à un texte vérifiable que l'on peut citer et corriger. Le LLM <b>propose</b> ; il ne confirme jamais."),
              img("rag_flow.png", 16.8, "Figure 3 — Du signal à l'hypothèse : texte de symptômes, récupération TF-IDF des fiches, interprète."),
              P("4.2 La base de connaissances (les données du RAG)", "h2"),
              P("La base est le dossier <i>knowledge/</i> : <b>" + str(len(docs)) + " fiches Markdown</b> en français, de 75 à 205 mots chacune (781 mots au total). Chaque fiche commence par un en-tête "
                "(<i>id</i>, <i>label</i>, <i>title</i>) suivi du texte. Le <i>label</i> relie la fiche à une classe : <i>eclipse</i>, <i>dos_p2p</i>, <i>benign_restart</i>, <i>benign_burst</i> ou <i>reference</i> (connaissance générale, jamais choisie comme hypothèse)."),
              table([["id", "label", "Titre", "Contenu essentiel"],
                     ["eclipse", "eclipse", "Eclipse Attack (isolement P2P d'un nœud)", "Symptômes (diversité faible, blocs d'un seul pair, retard croissant, nombre de pairs normal), diagnostic différentiel avec le redémarrage, réponse recommandée"],
                     ["dos_p2p", "dos_p2p", "Déni de service P2P", "Flux de messages extrême, CPU saturé, mémoire en hausse, latence et erreurs RPC ; différence avec une rafale légitime ; réponse"],
                     ["restart_resync", "benign_restart", "Redémarrage et resynchronisation", "Très peu de pairs au début puis retour progressif, churn et retard qui décroissent : événement bénin"],
                     ["legit_burst", "benign_burst", "Rafale légitime de transactions", "Charge élevée mais modérée, courte, sans dégradation du service : pas d'attaque"],
                     ["baseline_normal", "reference", "Comportement normal d'un nœud", "Plages habituelles des métriques"],
                     ["devp2p_overview", "reference", "Aperçu de devp2p", "Rappel du fonctionnement du protocole P2P d'Ethereum (concepts)"]],
                    [3.4 * cm, 2.5 * cm, 3.8 * cm, 7.2 * cm]), Spacer(1, 4),
              P("Les fiches sont <b>défensives</b> : elles décrivent des symptômes observables, des diagnostics différentiels et des réponses, jamais une méthode d'attaque. "
                "<b>Pour ajouter une fiche</b> : créer un fichier <i>knowledge/xxx.md</i> avec l'en-tête <i>id/label/title</i>, puis relancer (l'index est reconstruit au démarrage). "
                "<b>Biais connu</b> : les fiches et le simulateur sont écrits par les mêmes auteurs ; la bonne récupération est donc en partie circulaire, et les résultats sur données réelles sont indispensables.", "box"),
              P("4.3 Index et récupération", "h2"),
              *bullets(["<b>Représentation</b> : <i>TfidfVectorizer</i> (scikit-learn) sur « titre + texte », minuscules, accents supprimés, mots et <b>bigrammes</b>, pondération sous-linéaire (<i>sublinear_tf</i>).",
                        "<b>Recherche</b> : similarité <b>cosinus</b> entre le texte de symptômes et chaque fiche ; les <b>3</b> fiches les plus proches sont retournées avec leur score.",
                        "<b>Aucun réseau ni GPU</b> : l'index tient en mémoire et se reconstruit en millisecondes ; c'est ce qui rend l'évaluation reproductible. Pour une version « embeddings », il suffit de remplacer le vectoriseur (même interface <i>retrieve(query, k)</i>)."]),
              P("4.4 Du signal au texte de symptômes", "h2"),
              P("La fonction <i>symptom_text</i> transforme les métriques de la fenêtre d'alerte en phrases, avec des seuils fixes : topologie, mémoire, erreurs et synchronisation sont comparées à la <b>baseline</b> (z-score) ; "
                "les magnitudes de charge (messages, CPU, latence RPC) sont comparées à l'<b>historique récent du nœud lui-même</b> (fenêtres t−30 à t−8). Cela évite de confondre un nœud habituellement chargé avec une surcharge soudaine."),
              table([["Métrique", "Formulation « anormale »", "Condition", "Formulation « normale »"],
                     ["peer_diversity", "diversité des pairs très faible", "z < −2", "diversité des pairs normale"],
                     ["single_source_ratio", "blocs reçus d'un seul pair", "z > 2", "blocs reçus de plusieurs pairs"],
                     ["peer_churn", "churn de pairs élevé", "z > 2", "churn de pairs normal"],
                     ["peer_count", "très peu de pairs", "z < −5", "nombre de pairs normal"],
                     ["sync_lag", "retard de synchronisation", "z > 2", "synchronisation à jour"],
                     ["msgs_in", "flux de messages élevé / extrême", "charge relative > 1,3 / > 2,5", "flux de messages normal"],
                     ["cpu", "CPU élevé / saturé", "charge relative > 1,3 / > 1,9", "CPU normal"],
                     ["mem", "mémoire en hausse", "z > 3", "mémoire stable"],
                     ["rpc_latency", "latence RPC élevée / extrême", "charge relative > 1,3 / > 2,5", "latence RPC normale"],
                     ["rpc_error", "erreurs RPC nombreuses", "z > 3", "aucune erreur RPC"]], [3.4 * cm, 4.6 * cm, 4.1 * cm, 4.8 * cm]), Spacer(1, 6),
              P("4.5 Les deux interprètes", "h2"),
              P("<b>OfflineInterpreter</b> (utilisé pour toutes les évaluations) : prend la meilleure fiche dont le <i>label</i> n'est pas <i>reference</i> ; si son score est inférieur à 0,05, l'hypothèse est <i>unknown</i>. "
                "Sinon l'hypothèse est celle du label (<i>eclipse</i>, <i>dos_p2p</i>, ou <i>benign</i> pour redémarrage et rafale), avec la similarité comme « confiance » et un texte de justification qui cite les symptômes et la fiche. "
                "Ce n'est <b>pas un LLM</b> : c'est de la récupération pure, choisie pour être déterministe et gratuite."),
              P("<b>MistralInterpreter</b> (implémenté, <b>non évalué</b>, faute de clé API pendant le développement) : envoie à l'API Mistral un prompt contenant les symptômes, le type suggéré par le ML et les 3 fiches, "
                "et exige une réponse JSON <i>{attack, confidence, rationale}</i> à température 0. Toute erreur (réseau, JSON invalide, clé absente) ramène à l'interprète offline : le pipeline ne bloque jamais."),
              code('Tu es un analyste sécurité Ethereum. À partir des symptômes et des fiches, propose UNE hypothèse.\n'
                   'Symptômes : <texte de symptômes>\nType suggéré par le modèle ML : <eclipse|dos_p2p>\n\nFiches :\n[id] titre\n<texte>...\n\n'
                   'Réponds uniquement en JSON : {"attack": "eclipse|dos_p2p|benign|unknown", "confidence": 0..1, "rationale": "2 phrases"}.\n'
                   "Tu ne confirmes jamais une attaque : tu proposes une hypothèse."),
              P("Pour l'activer : définir <i>MISTRAL_API_KEY</i> et instancier <i>MistralInterpreter(retriever)</i> à la place de l'interprète offline (voir le guide).")]
    if ragev:
        ex = ragev["example"]
        story += [P("4.6 Exemple complet", "h2"),
                  P("Alerte d'un run Eclipse simulé (graine 100). Texte de symptômes produit :"), code(ex["symptoms"].replace(", ", ",\n")),
                  table([["Rang", "Fiche", "Label", "Similarité cosinus"]] + [[str(i + 1), a, b, f"{s:.3f}"] for i, (a, b, s) in enumerate(ex["retrieved"])],
                        [1.5 * cm, 5.0 * cm, 4.0 * cm, 4.0 * cm]), Spacer(1, 4),
                  P(f"La fiche <i>eclipse</i> arrive en tête (0,41) devant <i>restart_resync</i> (0,29) : les deux évoquent un churn et un retard, mais seule l'Eclipse correspond à « nombre de pairs normal » avec une diversité très faible. "
                    f"Hypothèse : <b>{ex['hyp']}</b>. Elle est ensuite soumise à la confirmation.")]
        t = pd.DataFrame(ragev["table"]).fillna(0).astype(int)
        story += [P("4.7 Qualité de l'hypothèse sur les alertes (simulation)", "h2"),
                  P("Hypothèse (colonnes) selon la nature réelle du run (lignes), sur les alertes levées par le ML aux graines 100 à 102 :"),
                  table([["Nature réelle"] + list(t.columns)] + [[str(i)] + [str(int(v)) for v in row] for i, row in t.iterrows()], [4.6 * cm, 3 * cm, 3 * cm, 3 * cm]),
                  Spacer(1, 4),
                  P("Lecture : toutes les Eclipses sont reconnues (79/79) ; 78 des 90 DoS le sont, les autres sont jugés bénins (rafale confondue avec une attaque faible) ; "
                    "les redémarrages et rafales sont presque toujours écartés ; la maintenance, jamais vue, est prise pour un DoS dans 24 cas sur 44. "
                    "<b>Attention</b> : fiches et simulateur partagent les mêmes auteurs, donc ces taux sont probablement optimistes.", "box")]

    # ------------------------------------------------------------------ 5. corrélation + confirmation
    story += [P("5. Corrélation et confirmation", "h1"),
              P("Après l'hypothèse, EVA-Guard cherche des <b>preuves indépendantes</b> dans les mesures. Le <b>catalogue d'indicateurs est fermé</b> : pour chaque hypothèse, 5 indicateurs prédéfinis ; "
                "le LLM ne peut ni en inventer ni en retirer."),
              table(br.thresholds_table(), [2.4 * cm, 6.8 * cm, 1.7 * cm, 2.0 * cm, 4.0 * cm]), Spacer(1, 4),
              P("Un indicateur est « passé » si la valeur lissée dépasse le seuil <b>haut</b> (quantile 99 % de la baseline) ou passe sous le seuil <b>bas</b> (quantile 1 %). "
                "Les seuils viennent de la baseline apprise (ici, la graine 100) : ils sont donc propres au nœud observé.", "small"),
              img("confirmation.png", 16.8, "Figure 4 — Règle de confirmation, rejouée fenêtre par fenêtre."),
              P("5.1 La règle", "h2"),
              P(f"Une hypothèse est <b>CONFIRMÉE</b> si, pendant <b>p</b> fenêtres consécutives, au moins <b>k</b> indicateurs sont passés <b>et</b> proviennent d'au moins <b>{Rule().min_sources}</b> sources distinctes "
                f"(P2P, système, RPC). Le contrôle part de la fenêtre précédant l'alerte et s'arrête {config.CONFIRM_TIMEOUT} fenêtres après : sans satisfaction dans ce délai, le verdict est <b>NON CONFIRMÉE</b>. "
                "Le calcul est <b>causal</b> : il n'utilise jamais une fenêtre future."),
              code("pour tau de (t_alerte - 1) à (t_alerte + timeout):\n    preuves = [indicateur_passe(f, tau) pour f dans catalogue(hypothèse)]\n"
                   "    série = série + 1 si (nb_passés >= k et nb_sources_passées >= 2) sinon 0\n"
                   "    si série >= persistance et tau >= t_alerte:  retourner CONFIRMÉE à tau\nretourner NON CONFIRMÉE"),
              P("5.2 Paramètres choisis", "h2"),
              P("(k, sources minimales, persistance) est choisi sur le jeu de validation parmi 24 combinaisons (k ∈ {2,3,4}, sources ∈ {1,2}, persistance ∈ {1..4}) en maximisant le F1 puis, à égalité, la règle la plus stricte."),
              table([["Graine", "Seuil ML", "k", "Sources min.", "Persistance"]] + [[str(int(r.seed)), n(r.threshold, 3), str(int(r.k)), str(int(r.min_sources)), str(int(r.persistence))] for r in params.itertuples()],
                    [2.0 * cm, 3.0 * cm, 2.0 * cm, 3.0 * cm, 3.0 * cm]), Spacer(1, 6),
              P("5.3 Pourquoi cette conception", "h2"),
              *bullets(["<b>Explicable</b> : chaque verdict s'accompagne de la liste des indicateurs, de leurs valeurs et de leurs seuils.",
                        "<b>Robuste à un LLM faillible</b> : une hypothèse fausse ne suffit pas à déclencher une réponse ; il faut que les mesures concordent.",
                        "<b>Limite assumée</b> : si les indicateurs d'une hypothèse sont corrélés entre eux (même cause physique), la « multi-source » est moins indépendante qu'elle n'y paraît ; c'est une piste d'amélioration (contre-preuves, source externe)."])]

    # ------------------------------------------------------------------ 6. restitution, dashboard
    story += [P("6. Restitution et dashboard", "h1"),
              P("Le <i>ReportAgent</i> assemble un rapport textuel : alerte, hypothèse, décision, liste des preuves et recommandation (par exemple : « isoler le nœud, ajouter des pairs de confiance, vérifier la chaîne auprès d'une source indépendante » pour une Eclipse). "
                "Le <b>dashboard Streamlit</b> (<i>dashboard/app.py</i>) rend ces éléments visibles :"),
              *bullets(["<b>Rejeu des scénarios</b> : cinq cas pré-calculés (Eclipse, DoS, rafale, redémarrage, maintenance) avec un curseur de fenêtre, six onglets (détection, hypothèse et fiches citées, preuves et décision, chemin observé, comparaison des trois systèmes, rapport).",
                        "<b>Analyser une trace</b> : import d'un CSV du collecteur (ou d'un run de <i>results/runs</i>), avec référence simulée ou apprise sur vos runs normaux réels ; mêmes six onglets.",
                        "<b>Chemin observé</b> : ordre d'apparition des effets mesurés (voisinage, connexions, synchronisation ; ou trafic, ressources, service) avec la fenêtre de franchissement de chaque indicateur. C'est une lecture des symptômes, pas la méthode d'un attaquant.",
                        "<b>Résultats</b> et <b>Aide</b> : tableaux, figures, glossaire des métriques."]),
              P("Le fichier <i>dashboard/dashboard.html</i> est une version statique du rejeu, sans serveur.")]

    # ------------------------------------------------------------------ 7. évaluation
    story += [P("7. Évaluation", "h1"),
              P("7.1 Protocole", "h2"),
              P("Cinq graines (100 à 104) ; pour chacune : entraînement, sélection du seuil et de la règle sur la validation, puis évaluation sur 130 runs de test jamais utilisés. "
                "Métriques : précision, rappel, F1 (une attaque détectée = alerte avec un type), taux de fausses alertes (runs normaux ou bénins classés « attaque »), exactitude du type, délais de détection et de confirmation. "
                "Intervalles de confiance à 95 % par bootstrap sur les runs."),
              table([["Système", "Précision", "Rappel", "F1", "Fausses alertes", "Délai détection", "Délai confirmation"]] +
                    [[x["system"].replace(" : ML + LLM/RAG + agents + confirmation", ""), n(x["precision_mean"]), n(x["recall_mean"]), n(x["f1_mean"]), n(x["fpr_mean"]),
                      f"{x['detect_time_s_mean']:.0f} s", f"{x['confirm_time_s_mean']:.0f} s"] for x in summ],
                    [4.6 * cm, 1.9 * cm, 1.8 * cm, 1.6 * cm, 2.4 * cm, 2.3 * cm, 2.3 * cm]), Spacer(1, 4),
              img("comparison.png", 14.5, "Figure 5 — Comparaison des trois systèmes (moyenne sur 5 graines)."),
              P(f"<b>Lecture honnête.</b> Le contexte LLM/RAG fait passer les fausses alertes de {n(B1['fpr_mean'])} à {n(B2['fpr_mean'])} avec un rappel un peu plus bas ({n(B1['recall_mean'])} → {n(B2['recall_mean'])}). "
                f"La confirmation (EVA-Guard) n'améliore pas ce résultat ({n(EV['fpr_mean'])}) et ajoute {EV['confirm_time_s_mean']:.0f} s de délai. Sur ces données simulées, l'apport vient du contexte, pas de la confirmation ; "
                "les raisons possibles sont discutées dans le rapport principal (section 13).", "box"),
              P("7.2 Ablation", "h2"),
              table([["Variante", "Précision", "Rappel", "F1", "Fausses alertes"]] +
                    [[k, n(v["precision_mean"]), n(v["recall_mean"]), n(v["f1_mean"]), n(v["fpr_mean"])] for k, v in abl.items()], [6.4 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 3 * cm]), Spacer(1, 4),
              P("Retirer une source d'observation dégrade fortement les résultats (sans RPC : F1 " + n(abl["sans source RPC"]["f1_mean"]) + ") : les trois sources se complètent. Sans LLM/RAG, les fausses alertes remontent à " +
                n(abl["sans LLM/RAG (type ML)"]["fpr_mean"]) + ". Retirer la persistance ou l'exigence multi-source ne change presque rien, ce qui confirme que la confirmation n'est pas l'élément décisif ici."),
              img("fpr_by_type.png", 13.5, "Figure 6 — Fausses alertes par type d'événement bénin. La maintenance (jamais vue) reste difficile pour tous les systèmes.")]
    if sens is not None:
        piv = sens.pivot_table(index=["attack", "level"], columns="system", values="rappel").reset_index()
        rows = [["Attaque simulée", "Intensité", "Baseline 1", "Baseline 2", "EVA-Guard"]]
        for r in piv.itertuples(index=False):
            rows.append([{"eclipse": "Eclipse", "dos_p2p": "DoS P2P"}[r[0]], n(r[1], 1), n(r[2]), n(r[3]), n(r[4])])
        story += [P("7.3 Sensibilité à l'intensité de l'épisode", "h2"),
                  P("Le paramètre <i>intensity</i> du simulateur règle l'amplitude des effets (0,1 très faible → 1,0 forte). Les épisodes sont générés au niveau des <b>métriques</b> (aucun trafic) ; "
                    "3 graines × 12 runs par attaque et par niveau. Le tableau donne la part des épisodes pour lesquels le système classe le run comme attaque (le type n'est pas vérifié dans cette mesure)."),
                  img("sensitivity.png", 15.5, "Figure 7 — Rappel en fonction de l'intensité de l'épisode simulé."),
                  table(rows, [3.4 * cm, 2.4 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm]), Spacer(1, 4),
                  P("Lecture : en dessous d'une intensité d'environ 0,3, les épisodes faibles échappent à tous les systèmes, et les systèmes avec contexte ou confirmation perdent davantage que le ML seul "
                    "(qui, lui, signale aussi beaucoup de bénin). C'est la <b>zone grise</b> de la méthode : une attaque discrète et lente n'est pas distinguée du bruit. "
                    "Le délai de détection diminue quand l'intensité augmente (par exemple, DoS : de 40-60 s à 20 s).", "box")]
    rc = RES / "runs" / "real_check.csv"
    if rc.exists():
        r = pd.read_csv(rc)
        nm = {"normal": "Normal (test)", "benign_restart": "Redémarrage bénin", "benign_burst": "Rafale légitime"}
        story += [P("7.4 Contrôle sur traces réelles bénignes", "h2"),
                  P("Sur des runs réels d'un nœud Geth unique (mode <i>--dev</i>), aucun épisode offensif : seules des fausses alertes peuvent être comptées."),
                  table([["Système", "Type de run", "Runs", "Classés attaque", "Taux"]] + [[x.system, nm.get(x.run_type, x.run_type), str(x.runs), str(x.classes_attaque), n(x.taux)] for x in r.itertuples()],
                        [5.2 * cm, 4.2 * cm, 1.8 * cm, 3.0 * cm, 1.8 * cm]), Spacer(1, 4),
                  P("Aucun système n'a produit de fausse alerte, mais l'expérience ne départage pas les systèmes et ne mesure pas le rappel (aucune attaque réelle ; 3 à 4 runs par type ; nœud sans pairs).", "box")]

    # ------------------------------------------------------------------ 8. contrats
    story += [P("8. Contrats de données entre agents", "h1"),
              P("Les agents échangent des objets JSON définis dans <i>eva_guard/schemas.py</i>. Ils permettent de remplacer un agent (par exemple l'interprète) sans toucher aux autres."),
              code('Alert      {t, score, suspected_type, top_features: [[métrique, z-score], ...]}\n'
                   'Hypothesis {attack: eclipse|dos_p2p|benign|unknown, confidence, rationale, cited_docs: [id],\n            evidence_to_check: [[métrique, high|low]], backend}\n'
                   'Evidence   {indicator, source: P2P|SYS|RPC, value, threshold, direction: high|low, passed}\n'
                   'Decision   {verdict: CONFIRMED|NOT_CONFIRMED|NO_ALERT, attack, t_decision, reason,\n            evidence: [Evidence], rule: {k, min_sources, persistence, timeout}}'),
              P("Le fichier <i>results/cases.json</i> (alimentant le dashboard) ajoute à ces objets les séries de métriques, les scores, le seuil et le « chemin observé »."),
              P("9. Limites et risques", "h1"),
              *bullets(["<b>Données simulées</b> : profils écrits par les auteurs ; les chevauchements attaque faible / charge forte sont des hypothèses. Les chiffres ne se transposent pas tels quels à un vrai nœud.",
                        "<b>Fiches et simulateur du même auteur</b> : la bonne récupération des fiches est probablement optimiste.",
                        "<b>Traces réelles bénignes uniquement</b> : le rappel réel n'est pas mesuré ; les épisodes d'attaque exigent un cadre validé par l'encadrant.",
                        "<b>Nœud unique en mode développement</b> : pas de pairs, donc les métriques de topologie sont constantes ; <i>msgs_in</i> et <i>single_source_ratio</i> ne sont pas collectés.",
                        "<b>Interprète Mistral non évalué</b> ; un LLM réel peut se tromper, d'où la confirmation déterministe.",
                        "<b>net_io dérivée de bytes_in</b> (collecteur et simulateur) : cette métrique « système » n'est pas indépendante de la source P2P ; l'indépendance réelle des sources est donc inférieure à ce que suggère la classification.",
                        "<b>Un épisode et une alerte par run</b>, pas de dérive lente de la baseline."]),
              P("10. Pistes d'amélioration", "h1"),
              *bullets(["Enregistrer plus de runs réels (au moins 3 par profil) et des traces d'attaque autorisées pour mesurer le rappel.",
                        "Ajouter des <b>contre-preuves</b> (indicateurs dont la présence réfute l'hypothèse) et une <b>source indépendante</b> (second nœud, explorateur de blocs) à la confirmation.",
                        "Évaluer l'interprète Mistral et comparer à l'interprète offline sur les mêmes alertes.",
                        "Collecter <i>msgs_in</i> et <i>single_source_ratio</i> (compteurs Prometheus vérifiés, journaux Geth) ; passer à un réseau multi-nœuds.",
                        "Adaptation continue de la baseline (dérive), plusieurs épisodes par run, scénario optionnel RPC flooding."]),
              P("11. Glossaire", "h1"),
              table([["Terme", "Définition"],
                     ["Eclipse", "Situation où un nœud n'est entouré que de pairs d'un même acteur et perd sa vue indépendante du réseau."],
                     ["DoS P2P", "Saturation d'un nœud par un flux anormal de messages pair-à-pair."],
                     ["Fenêtre", "Intervalle de 10 s regroupant les métriques observées."],
                     ["Baseline", "Statistiques du comportement normal (moyenne, écart-type, quantiles 1 % et 99 %)."],
                     ["Isolation Forest", "Modèle non supervisé qui isole les points anormaux en peu de coupes aléatoires."],
                     ["Random Forest", "Ensemble d'arbres de décision votant pour une classe."],
                     ["RAG", "Génération augmentée par récupération : on fournit au modèle des documents de référence retrouvés par similarité."],
                     ["TF-IDF", "Pondération des mots selon leur fréquence dans un document et leur rareté dans l'ensemble des documents."],
                     ["Similarité cosinus", "Mesure de proximité entre deux vecteurs de mots (1 = identiques, 0 = rien en commun)."],
                     ["Indicateur", "Métrique comparée à un seuil de la baseline, utilisée comme preuve."],
                     ["Persistance", "Nombre de fenêtres consécutives pendant lesquelles la règle de confirmation doit tenir."],
                     ["FPR", "Taux de fausses alertes : part des runs normaux ou bénins classés « attaque »."]], [3.6 * cm, 13.4 * cm])]

    doc = TDoc(str(OUT))
    doc.multiBuild(story)
    print("écrit", OUT)


if __name__ == "__main__":
    main()
