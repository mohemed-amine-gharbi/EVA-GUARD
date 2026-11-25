"""Construit le rapport PDF détaillé à partir des résultats réels (results/*.json|csv, figures, cas d'étude).

    python report/build_report.py   ->   report/EVA-Guard_Rapport.pdf
Tous les chiffres du rapport sont lus dans results/ : relancez `python run_all.py` puis ce script pour les mettre à jour.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image,
                                PageBreak, KeepTogether, Preformatted)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RES = ROOT / "results"
FIG = RES / "figures"
OUT = ROOT / "report" / "EVA-Guard_Rapport.pdf"
_enc = ROOT / "report" / "encadrant.txt"          # écrivez-y le nom de l'encadrant (une ligne)
ENCADRANT = _enc.read_text(encoding="utf-8").strip() if _enc.exists() and _enc.read_text(encoding="utf-8").strip() else "[Nom de l'enseignant]"

import os
import matplotlib
FD = os.path.join(matplotlib.get_data_path(), "fonts", "ttf") + os.sep   # polices DejaVu fournies avec matplotlib (Windows/Linux/macOS)
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", FD + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DV-M", FD + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

ACC = colors.HexColor("#d1603d")
INK = colors.HexColor("#222222")
S = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.4, leading=13.6, alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="DV", fontSize=8, leading=11, textColor=colors.HexColor("#555555")),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8, leading=10.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=8, leading=10.5, textColor=colors.white),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=19, textColor=ACC, spaceBefore=14, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11.2, leading=15, textColor=INK, spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "cap": ParagraphStyle("cap", fontName="DV-I", fontSize=8, leading=10.5, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=10),
    "toch": ParagraphStyle("toch", fontName="DV-B", fontSize=15, leading=19, textColor=ACC, spaceAfter=8),
    "title": ParagraphStyle("title", fontName="DV-B", fontSize=26, leading=32, textColor=ACC, alignment=TA_CENTER),
    "sub": ParagraphStyle("sub", fontName="DV", fontSize=13, leading=18, textColor=INK, alignment=TA_CENTER),
    "bul": ParagraphStyle("bul", fontName="DV", fontSize=9.4, leading=13.4, leftIndent=14, bulletIndent=3, textColor=INK, spaceAfter=2),
    "box": ParagraphStyle("box", fontName="DV", fontSize=9, leading=13, textColor=INK, backColor=colors.HexColor("#fdf1ec"),
                          borderPadding=7, borderColor=ACC, borderWidth=0.8, spaceBefore=6, spaceAfter=12, leftIndent=8, rightIndent=8),
    "code": ParagraphStyle("code", fontName="DV-M", fontSize=7.4, leading=9.6, backColor=colors.HexColor("#f4f4f4"), borderPadding=5,
                           spaceBefore=4, spaceAfter=8),
}


def P(t, s="body"):
    return Paragraph(t, S[s])


def bullets(items):
    return [Paragraph(i, S["bul"], bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=True, align_right_from=None):
    data = []
    for ri, r in enumerate(rows):
        data.append([Paragraph(str(c), S["cellb"] if (header and ri == 0) else S["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d9d9")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), ACC))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f7f7")))
    t.setStyle(TableStyle(st))
    return t


def img(name, width_cm, caption):
    p = FIG / name
    from PIL import Image as PI
    w, h = PI.open(p).size
    im = Image(str(p), width=width_cm * cm, height=width_cm * cm * h / w)
    return KeepTogether([im, P(caption, "cap")])


def n(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def pm(m, s, d=2):
    return f"{n(m, d)} ± {n(s, d)}"


class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=2.1 * cm, rightMargin=2.1 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm,
                         title="EVA-Guard — Rapport de projet", author="Équipe EVA-Guard", **kw)
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=self.deco)])

    def deco(self, canv, doc):
        canv.saveState()
        canv.setFont("DV", 7.5)
        canv.setFillColor(colors.HexColor("#777777"))
        if doc.page > 1:
            canv.drawString(2.1 * cm, A4[1] - 1.3 * cm, "EVA-Guard — Détection et confirmation agentiques des attaques ciblant les nœuds Ethereum")
            canv.drawRightString(A4[0] - 2.1 * cm, 1.2 * cm, f"{doc.page}")
        canv.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            self.notify("TOCEntry", (0 if fl.style.name == "h1" else 1, fl.getPlainText(), self.page))


def load():
    summ = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    abl = json.loads((RES / "ablation_summary.json").read_text(encoding="utf-8"))
    params = pd.read_csv(RES / "selected_params.csv")
    cases = json.loads((RES / "cases.json").read_text(encoding="utf-8"))
    return summ, abl, params, cases


def thresholds_table():
    from eva_guard.simulator import generate_dataset
    from eva_guard.features import smooth, BaselineStats
    from eva_guard.config import CATALOG, SOURCE, DESCRIPTION
    params = pd.read_csv(RES / "selected_params.csv")
    d = generate_dataset(int(params.seed.iloc[0]), {"train": {"normal": 30, "eclipse": 1, "dos_p2p": 1}})
    st = BaselineStats(smooth(d["train"]))
    rows = [["Hypothèse", "Indicateur", "Source", "Sens", "Seuil (baseline, p1/p99)"]]
    for a, items in CATALOG.items():
        for f, dr in items:
            rows.append([a, f"{f} — {DESCRIPTION[f]}", SOURCE[f], "supérieur" if dr == "high" else "inférieur", n(st.threshold(f, dr), 3)])
    return rows


def main():
    summ, abl, params, cases = load()
    B1, B2, EV = summ
    ab = {a["system"]: a for a in abl}
    story = []
    # ------------------------------------------------------------------ couverture
    story += [Spacer(1, 4.5 * cm), P("EVA-Guard", "title"), Spacer(1, 0.4 * cm),
              P("Détection et confirmation agentiques des attaques<br/>ciblant les nœuds Ethereum", "sub"), Spacer(1, 1.2 * cm),
              P("Rapport de mini-projet — Matière Blockchain", "sub"), Spacer(1, 0.3 * cm),
              P("ENIS — École Nationale d'Ingénieurs — Génie informatique", "sub"), Spacer(1, 2.0 * cm),
              P("Équipe : Mohamed Amine Gharbi — Baya Sayah — Hadil Kharoubi — Hedi Gouia<br/>Encadrant : " + ENCADRANT, "sub"), Spacer(1, 2.0 * cm),
              P(f"Version du {date.today().strftime('%d/%m/%Y')}", "sub"), Spacer(1, 2.5 * cm),
              P("<b>Lecture obligatoire avant d'utiliser les résultats.</b> Tous les chiffres de ce rapport proviennent d'une "
                "évaluation sur <b>télémétrie simulée</b> (voir section 6). Ils valident le fonctionnement de la chaîne et la "
                "méthode d'évaluation, mais ne prouvent rien sur de vrais nœuds Ethereum tant que des traces réelles ne sont pas "
                "utilisées. Les champs entre crochets sont à compléter par l'équipe.", "box"), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t1", fontName="DV-B", fontSize=9.5, leading=14, leftIndent=0),
                       ParagraphStyle("t2", fontName="DV", fontSize=8.5, leading=12, leftIndent=14)]
    story += [P("Table des matières", "toch"), toc, PageBreak()]

    # ------------------------------------------------------------------ 1. résumé
    story += [P("1. Résumé", "h1"),
              P("Les nœuds Ethereum sont exposés à des attaques réseau qui dégradent leur disponibilité, leur connectivité P2P ou "
                "leur synchronisation. Un modèle de Machine Learning ou un LLM qui signale une anomalie produit une <i>hypothèse</i>, "
                "pas une <i>preuve</i>. EVA-Guard est un prototype qui sépare explicitement <b>détection</b> et <b>confirmation</b> : "
                "un modèle ML lève l'alerte, un agent LLM + RAG formule une hypothèse d'attaque, un agent de corrélation collecte des "
                "preuves dans un catalogue fermé d'indicateurs (P2P, système, RPC), et un agent de confirmation applique une règle "
                "explicite et déterministe avant que l'agent de restitution n'explique la décision."),
              P("Le prototype couvre les deux scénarios obligatoires (Eclipse Attack, DoS par flooding P2P). Il est évalué sur 5 "
                "graines aléatoires (650 runs de test au total, dont 300 offensifs) contre deux baselines : ML seul et ML + LLM/RAG."),
              P("<b>Résultats principaux (télémétrie simulée).</b>"),
              *bullets([
                  f"Le contexte LLM/RAG réduit fortement les faux positifs : {n(B1['fpr_mean'])} (ML seul) → {n(B2['fpr_mean'])} (ML + LLM/RAG), "
                  f"F1 {n(B1['f1_mean'])} → {n(B2['f1_mean'])}.",
                  f"EVA-Guard complet obtient F1 = {n(EV['f1_mean'])} et un taux de faux positifs de {n(EV['fpr_mean'])}. "
                  f"<b>Il n'améliore pas</b> la Baseline 2 (F1 {n(B2['f1_mean'])}, faux positifs {n(B2['fpr_mean'])}) : les intervalles de "
                  f"confiance se recouvrent, le rappel baisse de {n(B2['recall_mean'] - EV['recall_mean'])} et le temps de confirmation "
                  f"ajoute {n(EV['confirm_time_s_mean'], 0)} s.",
                  "Le cas le plus difficile est une variante bénigne jamais vue à l'entraînement (maintenance/synchronisation lourde) : "
                  f"{n(EV['fpr_benign_maintenance_mean'])} de ces runs sont encore classés « attaque » par EVA-Guard.",
                  "L'étude ablative montre que les trois sources de preuves sont nécessaires au rappel et que l'exigence multi-sources "
                  "et la persistance ne réduisent pas les faux positifs dans ce simulateur."]),
              P("La question scientifique centrale reste donc <b>ouverte</b> : sur ces données, la confirmation multi-sources n'a pas "
                "démontré de gain sur ML + LLM/RAG. La section 11 analyse pourquoi et propose les expériences qui permettront de "
                "trancher avec de vraies traces.")]

    # ------------------------------------------------------------------ 2. intro
    story += [P("2. Introduction et problématique", "h1"),
              P("<b>Contexte.</b> Un nœud Ethereum échange en continu des messages avec ses pairs (couche devp2p), traite des requêtes RPC "
                "et consomme des ressources système. Les attaques ciblant le nœud se manifestent par des symptômes observables : peu de "
                "diversité parmi les pairs, retard de synchronisation, débit de messages anormal, saturation CPU/mémoire, erreurs RPC. "
                "Les approches récentes combinent monitoring, ML et LLM."),
              P("<b>Problème.</b> Une anomalie n'est pas une attaque. Un redémarrage, une resynchronisation ou une rafale légitime de "
                "transactions produisent des symptômes proches. Sans vérification indépendante, les alertes génèrent de nombreux faux positifs."),
              P("<b>Problématique.</b> Comment concevoir un système agentique capable de surveiller un nœud Ethereum, détecter une anomalie, "
                "interpréter le scénario probable et confirmer l'attaque par des preuves multi-sources ?"),
              P("<b>Question scientifique.</b> Une architecture agentique fondée sur plusieurs sources de preuves distingue-t-elle mieux une "
                "véritable attaque d'une simple anomalie, et réduit-elle les faux positifs par rapport à ML seul et à ML + LLM ?"),
              P("<b>Contributions de ce travail :</b>"),
              *bullets(["une architecture à cinq agents avec des contrats de données JSON entre agents ;",
                        "une règle de confirmation explicite et paramétrable (k indicateurs, sources minimales, persistance) ;",
                        "un banc d'essai reproductible (simulateur de télémétrie, 5 graines, intervalles de confiance, ablation) ;",
                        "un collecteur réel pour un nœud Geth (RPC + métriques), un dashboard et une base de connaissances RAG ;",
                        "une évaluation honnête, y compris des résultats négatifs, avec l'analyse de leurs causes."])]

    # ------------------------------------------------------------------ 3. biblio
    story += [P("3. Étude bibliographique", "h1"),
              P("Les trois documents ci-dessous ont été <b>lus en texte intégral</b> (fiches détaillées : <i>docs/fiches/</i>). Les chiffres cités sont recopiés des tableaux des articles ; "
                "les figures n'ont été relues visuellement que pour le Tableau 1 de l'article sur l'Eclipse. Les passages « notre analyse » sont nos commentaires, pas ceux des auteurs."),
              P("<b>Écart avec le cahier des charges.</b> Les références du cahier des charges ne correspondent pas exactement aux fichiers fournis ; nous citons ce que les fichiers contiennent :", "box"),
              table([["Cahier des charges", "Document réellement lu", "Nature"],
                     ["Houssel et al., eX-NIDS (2026), Comput. Electr. Eng. 129, 110826",
                      "Houssel, Layeghy, Singh, Portmann, <i>eX-NIDS</i>, arXiv:2507.16241v1 (juillet 2025, soumis à Elsevier)", "Preprint ; revue et volume non vérifiés"],
                     ["Rehman et al. (2026), J. Netw. Comput. Appl. 246, 104416 (détection d'Eclipse)",
                      "Rehman, Gregory, Gondal, Dong, Ge, <i>Eclipse Attacks in Blockchain Networks</i>, IEEE Access 13, 25918-25933, 2025",
                      "Article de synthèse (survey), sans expérience propre"],
                     ["Rosa-Bilbao et al. (2025), Comput. Stand. Interfaces 91, 103882 (CEP pour blockchains)",
                      "Rosa-Bilbao, Guitarte-Fernández, Boubeta-Puig, <i>A distributed complex event processing system…</i>, Computing 108:128, 2026",
                      "Système CEP distribué pour l'IoT ; pas de blockchain"]],
                    [4.6 * cm, 8.0 * cm, 4.3 * cm]),
              Spacer(1, 4),
              P("À confirmer avec l'encadrant : si l'article de surveillance de blockchains par CEP (Computer Standards &amp; Interfaces) est bien celui attendu, il faudra l'ajouter ; "
                "le document lu ici n'en traite pas.", "small"),

              P("3.1 eX-NIDS : expliquer les alertes d'un NIDS avec un LLM", "h2"),
              P("<b>Problème.</b> Les NIDS à base de ML détectent bien mais n'expliquent pas leurs alertes ; les méthodes d'explicabilité classiques exigent de l'expertise ML et n'utilisent pas de connaissance externe. "
                "Le LLM n'est pas utilisé pour détecter mais pour expliquer un flux déjà classé malveillant (p. 1-2, 4)."),
              P("<b>Architecture.</b> Flux NetFlow → NIDS ML (classification) → pour les flux malveillants, un <i>Prompt Augmenter</i> ajoute au prompt (i) la spécification des champs NetFlow, (ii) les noms de protocoles, "
                "(iii) pour chaque IP : renseignement de menace (CTI), géolocalisation et historique des flux → LLM → explication en texte libre (Fig. 4-6, p. 7-9). Les auteurs n'utilisent pas de RAG : "
                "les données étant structurées, une base classique suffit (p. 9-10). LLM : Llama3-70B-Instruct et GPT-4 (<i>gpt-4-1106-preview</i>)."),
              P("<b>Évaluation.</b> 50 flux malveillants du jeu NF-CSE-CIC-IDS2018-v2, jugés à la main par deux experts sur trois métriques binaires (correction, cohérence des features, cohérence factuelle). "
                "Avec GPT-4, l'enrichissement fait passer la correction de 40 % à 80 %, la cohérence des features de 96 % à 100 % et la cohérence factuelle de 78 % à 92 % ; avec Llama3 : 26 → 36 %, 84 → 100 %, 42 → 90 % (Table 1, p. 12). "
                "Le prompt est environ cinq fois plus long (2 308 contre 461 tokens) et le coût estimé passe de 5,75 $ à 10,37 $ pour 1 000 requêtes (p. 12)."),
              *bullets(["<b>Forces.</b> L'enrichissement améliore les trois métriques pour les deux modèles ; l'évaluation vise la <i>justesse</i> des explications, pas seulement leur lisibilité ; typologie des erreurs du LLM (valeurs inventées, features mal référencées, valeurs mal interprétées).",
                        "<b>Limites.</b> La correction reste faible pour Llama3 (36 %) et les auteurs jugent que des travaux sont nécessaires avant un usage critique (p. 13) ; échantillon de 50 flux, un seul jeu de données, deux évaluateurs (p. 10-11) ; "
                        "<i>notre analyse</i> : aucune confirmation indépendante de l'alerte ni de l'explication, et les faux positifs ne sont pas évalués (seuls les flux malveillants le sont).",
                        "<b>Réutilisé dans EVA-Guard.</b> Le principe « le LLM explique, il ne détecte pas » ; l'enrichissement du prompt par un contexte externe (chez nous : fiches de diagnostic via RAG) ; "
                        "la consigne de citer des valeurs observées ; les trois métriques comme idée d'évaluation des explications (non encore appliquées)."])
              ,
              P("3.2 Eclipse Attacks in Blockchain Networks : synthèse sur l'attaque, sa détection et sa prévention", "h2"),
              P("<b>Nature.</b> Article de synthèse qualitatif : il ne propose ni méthode nouvelle, ni expérience, ni jeu de données (p. 25918). Il décrit une attaque Eclipse comme la monopolisation des connexions d'un nœud pour l'isoler du réseau."),
              P("<b>Contenu.</b> Taxonomie (Fig. 2, p. 25920) en trois types d'attaque, trois familles de détection (surveillance réseau avec outils comme Wireshark ou Snort, audit des listes de pairs, vérification du consensus "
                "par recoupement avec des sources externes) et deux stratégies de prévention (durcissement de la découverte de pairs, diversité réseau et limites de connexions). Impacts : retard de confirmation, perturbation du consensus, double dépense, gaspillage de ressources, fuites de données (Section IV). "
                "Pour Ethereum, le texte cite la table de pairs de type Kademlia et sa politique d'éviction ; il ne mentionne ni discv4/discv5 ni le DoS P2P."),
              P("<b>Chiffres.</b> Les seuls chiffres sont ceux du Tableau 1 (p. 25925), sans source ni méthode : confirmation de transaction 10-15 s contre 30-60 s, durée de consensus environ 1 min contre plus de 3 min, "
                "succès de double dépense moins de 0,01 % contre plus de 25 %, utilisation des ressources 150-200 %. Ce sont des ordres de grandeur illustratifs, pas des mesures."),
              *bullets(["<b>Forces.</b> Vue d'ensemble claire (taxonomie, impacts, comparaison Bitcoin / Ethereum / Hyperledger / Polkadot, Tableau 2) ; liste de pistes de prévention et de recherche ; mise en évidence du lien entre isolement réseau et impact applicatif.",
                        "<b>Limites.</b> Aucune évaluation empirique, donc aucun taux de détection ni de fausses alertes ; chiffres du Tableau 1 non sourcés ; quelques citations douteuses relevées à la relecture (par exemple un outil attribué à une mauvaise référence) ; peu de détails spécifiques au protocole P2P d'Ethereum.",
                        "<b>Réutilisé dans EVA-Guard.</b> Les symptômes observables d'une Eclipse (appauvrissement et uniformisation des pairs, divergence avec le reste du réseau, retard de synchronisation) alimentent nos indicateurs et nos fiches RAG ; "
                        "la détection « par recoupement externe » correspond à notre exigence de source indépendante. Écart : l'article n'apporte pas de méthode de détection à comparer ; nos baselines sont les nôtres."]),

              P("3.3 Système CEP distribué edge-fog-cloud", "h2"),
              P("<b>Problème.</b> Un moteur de traitement d'événements complexes (CEP) centralisé devient un goulot d'étranglement quand des capteurs nombreux et hétérogènes produisent des flux continus (p. 1-2). "
                "L'article propose un CEP distribué en trois couches et l'évalue sur du matériel léger. Il traite l'IoT (cas d'étude : hôpital), pas la blockchain."),
              P("<b>Architecture.</b> Edge : capteurs publiant des événements simples dans des topics Kafka → Fog : moteurs CEP Esper (patterns EPL à seuils) produisant des événements complexes par domaine → "
                "Cloud : moteur CEP qui corrèle les événements de plusieurs domaines et émet des alertes (Fig. 3, p. 9). Chaque pattern est placé sur un seul moteur, de façon statique (p. 10)."),
              P("<b>Résultats.</b> Pic de 68 027 événements traités par seconde, puis 60 241 à saturation (Table 7, p. 17). Dans la comparaison contrôlée (Table 8, p. 18), les modes centralisé et distribué produisent le même nombre d'alertes (4 937) ; "
                "à 2 000 événements/s, la latence moyenne passe de 43 580 ms à 1 860 ms. Les auteurs précisent que ce gain vaut pour ce déploiement et ne se généralise pas (p. 19)."),
              *bullets(["<b>Forces.</b> Évaluation chiffrée avec trois répétitions et artefacts publiés ; conception configurable (patterns et topics externalisés) ; honnêteté sur les limites de la distribution.",
                        "<b>Limites.</b> Données simulées uniquement ; allocation statique, sans équilibrage ni reprise sur panne ; règles à seuils simples, et ni taux de détection ni faux positifs mesurés.",
                        "<b>Réutilisé dans EVA-Guard.</b> Le vocabulaire événement simple / complexe / alerte ; l'idée de corréler des événements de domaines différents (ici « frigo haut ET labo haut ») comme forme de confirmation multi-sources ; "
                        "des événements horodatés avec identifiant de source, pour la traçabilité des preuves. Écart : pas de ML, de LLM ni de persistance temporelle ; Kafka + Esper serait disproportionné pour ce mini-projet."]),

              P("3.4 Synthèse comparative et positionnement d'EVA-Guard", "h2"),
              table([["", "eX-NIDS", "Synthèse Eclipse", "CEP distribué", "EVA-Guard"],
                     ["Cible", "Flux réseau IP", "Blockchains (Eclipse)", "Capteurs IoT", "Nœuds Ethereum (Eclipse, DoS P2P)"],
                     ["Détection", "NIDS ML (en amont)", "Synthèse de méthodes", "Seuils (EPL)", "ML (Isolation Forest + Random Forest)"],
                     ["Rôle du LLM", "Explication", "Aucun", "Aucun", "Hypothèse + explication (RAG)"],
                     ["Preuves multi-sources", "Non (CTI par IP)", "Recoupement externe cité", "Corrélation de domaines", "Indicateurs sur 3 sources (P2P, système, RPC)"],
                     ["Confirmation", "Aucune", "Discutée, non évaluée", "Corrélation cloud", "Règle déterministe (k, sources, persistance)"],
                     ["Évaluation", "50 flux, 2 experts", "Aucune", "Latence et débit", "Simulée (5 graines) + faux positifs réels"]],
                    [2.6 * cm, 3.3 * cm, 3.5 * cm, 3.2 * cm, 4.3 * cm]),
              Spacer(1, 4),
              P("<b>Positionnement.</b> Aucun des trois documents ne combine détection, explication par LLM et confirmation par preuves indépendantes sur Ethereum. "
                "eX-NIDS couvre le chaînage « alerte ML → contexte → LLM » ; la synthèse sur l'Eclipse fournit la connaissance du domaine ; le CEP fournit le modèle événementiel et la corrélation de domaines. "
                "EVA-Guard ajoute une décision finale <b>non déléguée au LLM</b>, fondée sur des indicateurs observables : eX-NIDS montre justement que la sortie d'un LLM, même enrichie, peut rester incorrecte (correction de 36 % à 80 % selon le modèle). "
                "Cette combinaison est notre apport ; il n'est validé que dans les limites décrites aux sections 11 à 13.", "box")]

    # ------------------------------------------------------------------ 4. architecture
    story += [P("4. Architecture d'EVA-Guard", "h1"),
              P("Chaîne fonctionnelle : nœud Ethereum → collecte multi-source (P2P + système + RPC) → détection ML → agent d'interprétation "
                "(LLM + RAG) → hypothèse → corrélation des preuves → confirmation → CONFIRMÉE / NON CONFIRMÉE → rapport et recommandation. "
                "Le LLM ne confirme jamais seul."),
              table([["Agent", "Entrée", "Sortie (JSON)", "Technique", "Fichier"],
                     ["Détection", "Fenêtres de 10 s (12 features lissées)", "alert {t, score, type suspecté, top features}", "Isolation Forest + Random Forest", "eva_guard/detector.py"],
                     ["Interprétation", "Alerte + symptômes en langage naturel + fiches RAG", "hypothesis {attack, confiance, justification, preuves à chercher}", "RAG TF-IDF + interprète offline ou Mistral", "eva_guard/llm.py, rag.py"],
                     ["Corrélation", "Hypothèse + séries", "evidence_pack [{indicateur, source, valeur, seuil, passé}]", "Python, catalogue fermé", "eva_guard/agents.py"],
                     ["Confirmation", "Paquet de preuves", "decision {CONFIRMED / NOT_CONFIRMED, règle, raison}", "Règle déterministe", "eva_guard/agents.py"],
                     ["Restitution", "Alerte + hypothèse + décision", "Rapport et recommandation", "Gabarit (LLM optionnel)", "agents.py, dashboard/"]],
                    [2.5 * cm, 3.4 * cm, 4.2 * cm, 3.2 * cm, 3.5 * cm]),
              Spacer(1, 6),
              P("<b>Principes de conception.</b>"),
              *bullets(["<b>Catalogue fermé d'indicateurs</b> par hypothèse : le LLM ne peut pas inventer de preuve, il sélectionne dans une liste connue.",
                        "<b>Confirmation déterministe</b> : la décision finale est reproductible et explicable, indépendante de la température ou de la version du LLM.",
                        "<b>Causalité</b> : à tout instant, chaque agent n'utilise que les fenêtres passées (le lissage est causal, la confirmation avance fenêtre par fenêtre).",
                        "<b>Contrats JSON</b> (eva_guard/schemas.py) : permettent à quatre personnes de développer en parallèle et de remplacer un agent sans toucher aux autres.",
                        "<b>Repli</b> : si l'API Mistral est indisponible, l'interprète bascule sur l'interprète offline ; le pipeline ne s'arrête jamais."]),
              P("<b>Les trois systèmes comparés</b> partagent la même alerte ML (même seuil) : Baseline 1 décide à l'alerte ; Baseline 2 décide selon "
                "l'hypothèse du LLM/RAG ; EVA-Guard ajoute la corrélation et la confirmation par preuves.")]

    # ------------------------------------------------------------------ 5. environnement
    story += [P("5. Environnement Ethereum expérimental", "h1"),
              P("<b>Objectif.</b> Disposer d'un réseau Ethereum privé, isolé d'Internet, avec un nœud surveillé instrumenté, afin de collecter des "
                "données réelles de comportement normal (et, dans le cadre validé par l'encadrant, des épisodes anormaux)."),
              table([["Élément", "Choix", "Fichier"],
                     ["Réseau privé", "Docker + Kurtosis (ethereum-package), 3 paires Geth + Lighthouse", "infra/network_params.yaml"],
                     ["Métriques du nœud", "Geth avec --metrics, scrape Prometheus toutes les 5 s", "infra/prometheus.yml, geth_flags.txt"],
                     ["Métriques système", "node_exporter / cAdvisor, ou psutil sur le PID de Geth", "collectors/collector.py"],
                     ["Données RPC", "net_peerCount, eth_syncing, admin_peers, mesure de latence d'une requête de sonde", "collectors/collector.py"],
                     ["Format", "CSV : une ligne par fenêtre de 10 s, mêmes colonnes que le simulateur", "eva_guard/config.py"]],
                    [3.2 * cm, 9.2 * cm, 4.4 * cm]),
              Spacer(1, 6),
              P("<b>État de validation.</b> Le collecteur est testé contre un serveur JSON-RPC simulé (test automatisé : nombre de pairs, "
                "synchronisation, diversité par sous-réseaux /16). Il n'a <b>pas</b> été exécuté contre un vrai nœud Geth dans cet environnement ; "
                "la configuration Kurtosis n'a pas été lancée non plus. Ces deux étapes sont à réaliser par l'équipe (section 14)."),
              P("<b>Limite connue du collecteur.</b> La feature <i>single_source_ratio</i> (part des blocs reçus en premier du même pair) n'est pas "
                "disponible via le RPC standard ; elle est laissée vide, sauf si l'équipe ajoute un parseur des journaux Geth.")]

    # ------------------------------------------------------------------ 6. données
    from eva_guard.config import FEATURES, SOURCE, DESCRIPTION
    story += [P("6. Données : simulateur de télémétrie, features et jeux", "h1"),
              P("<b>Pourquoi un simulateur.</b> Au moment de la rédaction, aucune trace réelle d'attaque n'était disponible, et l'exécution des "
                "attaques elles-mêmes est du ressort de l'environnement isolé et de l'encadrant. Le simulateur (eva_guard/simulator.py) génère uniquement "
                "des <b>séries de métriques</b> (valeurs numériques par fenêtre) : il n'envoie aucun trafic et n'implémente aucune attaque. Il permet de "
                "construire, tester et évaluer toute la chaîne de détection et de confirmation de façon reproductible."),
              P("<b>Les 12 features</b> (une valeur par fenêtre de 10 s, lissées par une moyenne glissante causale de 3 fenêtres) :"),
              table([["Feature", "Source", "Signification"]] + [[f, SOURCE[f], DESCRIPTION[f]] for f in FEATURES], [3.6 * cm, 1.6 * cm, 11.6 * cm]),
              Spacer(1, 6),
              P("<b>Profils simulés.</b> Chaque run dure 100 fenêtres (≈ 16,7 min). La baseline normale inclut trois niveaux de charge (repos, modérée, "
                "élevée), du bruit autocorrélé et des décalages propres au run. Un épisode démarre entre les fenêtres 25 et 45 :"),
              *bullets(["<b>Eclipse</b> : diversité des pairs en baisse, blocs reçus du même pair, churn au début, retard de synchronisation croissant ; nombre de pairs quasi normal ; CPU/mémoire quasi inchangés. Intensité tirée au hasard (0,4 à 1).",
                        "<b>DoS P2P</b> : flux de messages, CPU, mémoire, latence et erreurs RPC en hausse, sur plusieurs sources. Intensité tirée au hasard (0,4 à 1) : les épisodes faibles ressemblent à de la charge forte.",
                        "<b>Redémarrage (bénin)</b> : peu de pairs puis remontée, churn et retard de sync qui décroissent, CPU et débit élevés pendant le rattrapage.",
                        "<b>Rafale légitime (bénin)</b> : hausse modérée de messages, CPU et latence, courte durée, sans erreurs ni croissance mémoire.",
                        "<b>Maintenance / synchronisation lourde (bénin, jamais vue)</b> : forte hausse de débit, CPU, mémoire et latence, quelques erreurs RPC. Présente uniquement dans le jeu de test, pour mesurer la généralisation."]),
              table([["Jeu", "Normal", "Eclipse", "DoS P2P", "Redémarrage", "Rafale", "Maintenance", "Total"],
                     ["Entraînement", "30", "20", "20", "—", "—", "—", "70"],
                     ["Validation", "10", "10", "10", "8", "8", "—", "46"],
                     ["Test", "25", "30", "30", "15", "15", "15", "130"]],
                    [2.8 * cm, 1.8 * cm, 1.8 * cm, 1.9 * cm, 2.6 * cm, 1.7 * cm, 2.5 * cm, 1.7 * cm]),
              Spacer(1, 4),
              P("Chaque graine régénère les trois jeux ; le découpage se fait <b>par run</b>, jamais par fenêtre, pour éviter toute fuite entre entraînement et test. "
                "Étiquettes par fenêtre : <i>in_event</i> (booléen), <i>run_type</i>, <i>onset</i>, <i>event_end</i>."),
              img("dataset_sample.png", 15.5, "Figure 1 — Un run de chaque type (jeu de test, graine 100), six features.")]

    # ------------------------------------------------------------------ 7. ML
    story += [P("7. Détection par Machine Learning", "h1"),
              P("<b>Normalisation.</b> Moyenne et écart-type appris sur les fenêtres normales de l'entraînement uniquement."),
              P("<b>Détecteur d'anomalie.</b> Isolation Forest (200 arbres) entraîné sur les seules fenêtres normales : il ne connaît pas les attaques. "
                "Le score d'anomalie est comparé à un seuil ; l'alerte est levée après 2 fenêtres consécutives au-dessus du seuil. Le seuil est choisi sur le "
                "jeu de validation pour maximiser le F1 de la <b>Baseline 1</b> (on ne désavantage donc pas la baseline)."),
              P("<b>Type suspecté.</b> Random Forest (200 arbres) entraîné sur les fenêtres normales et les fenêtres d'attaque (Eclipse, DoS). "
                "Il fournit le type suggéré pour la Baseline 1 et pour l'ablation « sans LLM/RAG ». Les épisodes bénins ne sont <b>pas</b> dans "
                "l'entraînement, ce qui reflète la difficulté réelle d'étiqueter tous les comportements légitimes."),
              img("importance.png", 9.5, "Figure 2 — Importance des features du Random Forest (graine 100)."),
              P("Les features qui discriminent le type sont celles attendues : diversité des pairs, synchronisation et part de blocs du même pair pour "
                "l'Eclipse ; messages, CPU, latence et erreurs pour le DoS.")]

    # ------------------------------------------------------------------ 8. RAG/LLM
    story += [P("8. Interprétation : LLM et RAG", "h1"),
              P("<b>Base de connaissances (knowledge/).</b> Six fiches en français : Eclipse, DoS par flooding P2P, redémarrage/resynchronisation, rafale légitime, "
                "fonctionnement normal, et une référence devp2p. Chaque fiche contient les symptômes observables, le diagnostic différentiel, les preuves à "
                "rechercher et la réponse recommandée. Ce sont des fiches de <b>diagnostic défensif</b>."),
              P("<b>Du signal au texte.</b> À l'alerte, les métriques sont converties en symptômes : topologie, synchronisation, mémoire et erreurs par "
                "z-score vs la baseline ; messages, CPU et latence par <b>rapport à l'historique récent du nœud</b> (fenêtres t-30 à t-8) pour ne pas "
                "confondre une charge habituelle élevée avec une surcharge soudaine."),
              P("<b>Récupération.</b> TF-IDF (unigrammes + bigrammes, sans accents) sur les fiches ; les 3 plus proches sont fournies à l'interprète. "
                "L'interface <i>retrieve(query, k)</i> permet de passer à des embeddings + ChromaDB sans toucher aux agents."),
              P("<b>Deux interprètes.</b> (1) <b>Offline</b> : la fiche non-référence la plus proche donne l'hypothèse (eclipse, dos_p2p ou bénin) ; "
                "c'est lui qui est évalué, pour la reproductibilité. (2) <b>Mistral</b> : prompt avec symptômes, type ML et fiches, réponse JSON imposée, "
                "repli sur l'offline en cas d'erreur ; implémenté mais <b>non évalué</b> ici (pas de clé API ni de réseau)."),
              P("<b>Biais à connaître.</b> Les fiches et le simulateur ont le même auteur : l'interprète offline en profite probablement. L'écart entre "
                "Baseline 1 et Baseline 2 est donc une borne optimiste de ce qu'apporterait un LLM + RAG sur des données réelles.", "box")]

    # ------------------------------------------------------------------ 9. confirmation
    story += [P("9. Corrélation et confirmation par preuves", "h1"),
              P("Pour une hypothèse d'attaque, l'agent de corrélation évalue cinq indicateurs d'un <b>catalogue fermé</b>. Chaque indicateur est comparé à un seuil "
                "appris sur la baseline normale (percentile 99 pour « supérieur », percentile 1 pour « inférieur ») sur la fenêtre lissée courante."),
              table(thresholds_table(), [2.2 * cm, 7.2 * cm, 1.6 * cm, 2.0 * cm, 3.8 * cm]),
              Spacer(1, 6),
              P("<b>Règle de confirmation.</b> L'hypothèse est CONFIRMÉE si, pendant <i>persistance</i> fenêtres consécutives (à partir de la première fenêtre anormale), "
                "au moins <i>k</i> indicateurs sur 5 dépassent leur seuil et proviennent d'au moins <i>min_sources</i> sources distinctes. Si la règle n'est pas "
                "satisfaite dans un délai de 8 fenêtres après l'alerte, la décision est NON CONFIRMÉE, avec la liste des preuves obtenues. Si l'hypothèse "
                "du LLM est « bénin » ou « inconnu », aucune confirmation n'est demandée."),
              P("<b>Sélection des paramètres.</b> k ∈ {2, 3, 4}, sources minimales ∈ {1, 2}, persistance ∈ {1, 2, 3, 4} sont choisis par recherche exhaustive sur "
                "le jeu de validation (maximum de F1, puis plus faible taux de faux positifs, puis règle la plus stricte). Valeurs retenues par graine :"),
              table([["Graine", "Seuil d'alerte", "k", "Sources min.", "Persistance"]] +
                    [[int(r.seed), n(r.threshold, 3), int(r.k), int(r.min_sources), int(r.persistence)] for r in params.itertuples()],
                    [2.5 * cm, 3.5 * cm, 2 * cm, 3 * cm, 3 * cm]),
              Spacer(1, 6),
              P("La validation ne contient pas la variante « maintenance » : la règle apprise n'a donc jamais vu ce type de comportement bénin.")]

    # ------------------------------------------------------------------ 10. protocole
    story += [P("10. Protocole d'évaluation", "h1"),
              *bullets(["<b>Graines.</b> 5 graines (100 à 104), jamais inspectées pendant le développement. La graine 0 a servi à déboguer ; c'est en l'inspectant (y compris son jeu de test) que le vocabulaire de symptômes de l'interprète et deux fiches (Eclipse, redémarrage) ont été corrigés, pour que les fiches décrivent correctement le nombre de pairs. Les graines finales n'ont donc pas influencé ces choix.",
                        "<b>Unité d'évaluation.</b> Le run : une prédiction « attaque (type) » ou « pas d'attaque » par run. 130 runs de test par graine : 60 offensifs, 70 non offensifs.",
                        "<b>Positifs.</b> Runs Eclipse et DoS. <b>Négatifs.</b> Normal, redémarrage, rafale, maintenance. Un run négatif classé « attaque » est un faux positif.",
                        "<b>Métriques.</b> Precision, Recall, F1, taux de faux positifs (aussi par type de run), exactitude du type d'attaque parmi les détections, temps de détection (début d'épisode → alerte), temps de confirmation (alerte → décision), médianes par graine.",
                        "<b>Incertitude.</b> Moyenne ± écart-type sur les graines ; intervalle de confiance bootstrap à 95 % (1000 rééchantillonnages des runs, toutes graines).",
                        "<b>Équité.</b> Les trois systèmes partagent la même alerte ML ; le seuil de la Baseline 1 est réglé pour son propre F1 sur la validation."])]

    # ------------------------------------------------------------------ 11. résultats
    story += [P("11. Résultats", "h1"), P("11.1 Comparaison des trois systèmes", "h2")]
    rows = [["Système", "Precision", "Recall", "F1", "Faux positifs", "Exact. du type", "Détect. (s)", "Confirm. (s)"]]
    for s in summ:
        rows.append([s["system"].split(" : ")[0], pm(s["precision_mean"], s["precision_std"]), pm(s["recall_mean"], s["recall_std"]),
                     pm(s["f1_mean"], s["f1_std"]), pm(s["fpr_mean"], s["fpr_std"]), n(s["type_acc_mean"]),
                     n(s["detect_time_s_mean"], 0), n(s["confirm_time_s_mean"], 0)])
    story += [table(rows, [2.3 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.3 * cm, 1.8 * cm, 1.9 * cm, 1.9 * cm]), Spacer(1, 4),
              P(f"Intervalles de confiance à 95 % (bootstrap) — F1 : Baseline 1 [{n(B1['f1_ci'][0])} ; {n(B1['f1_ci'][1])}], Baseline 2 [{n(B2['f1_ci'][0])} ; {n(B2['f1_ci'][1])}], "
                f"EVA-Guard [{n(EV['f1_ci'][0])} ; {n(EV['f1_ci'][1])}]. Faux positifs : Baseline 1 [{n(B1['fpr_ci'][0])} ; {n(B1['fpr_ci'][1])}], "
                f"Baseline 2 [{n(B2['fpr_ci'][0])} ; {n(B2['fpr_ci'][1])}], EVA-Guard [{n(EV['fpr_ci'][0])} ; {n(EV['fpr_ci'][1])}].", "small"),
              Spacer(1, 6),
              img("comparison.png", 16, "Figure 3 — Precision, Recall, F1 et taux de faux positifs (moyenne ± écart-type sur 5 graines)."),
              P(f"<b>Lecture.</b> (a) Baseline 1 → Baseline 2 : le contexte LLM/RAG divise les faux positifs par environ {n(B1['fpr_mean'] / B2['fpr_mean'], 1)} "
                f"({n(B1['fpr_mean'])} → {n(B2['fpr_mean'])}) et augmente la precision ({n(B1['precision_mean'])} → {n(B2['precision_mean'])}), au prix d'un rappel "
                f"plus faible ({n(B1['recall_mean'])} → {n(B2['recall_mean'])}) : certaines attaques faibles sont prises pour de la charge légitime. "
                f"(b) Baseline 2 → EVA-Guard : pas de gain. Les faux positifs sont équivalents ({n(B2['fpr_mean'])} vs {n(EV['fpr_mean'])}), le rappel baisse "
                f"({n(B2['recall_mean'])} → {n(EV['recall_mean'])}), et la décision arrive {n(EV['confirm_time_s_mean'], 0)} s plus tard en médiane. "
                "(c) Le type d'attaque est presque toujours correct quand une attaque est détectée."),
              KeepTogether([P("11.2 Faux positifs par type de run non offensif", "h2"),
                            img("fpr_by_type.png", 12.5, "Figure 4 — Part de runs non offensifs classés « attaque », par système.")]),
              table([["Système", "Normal", "Redémarrage", "Rafale légitime", "Maintenance (jamais vue)"]] +
                    [[s["system"].split(" : ")[0], pm(s["fpr_normal_mean"], s["fpr_normal_std"]), pm(s["fpr_benign_restart_mean"], s["fpr_benign_restart_std"]),
                      pm(s["fpr_benign_burst_mean"], s["fpr_benign_burst_std"]), pm(s["fpr_benign_maintenance_mean"], s["fpr_benign_maintenance_std"])] for s in summ],
                    [3 * cm, 2.6 * cm, 3 * cm, 3.2 * cm, 4.2 * cm]), Spacer(1, 6),
              P(f"<b>Lecture.</b> Aucun système ne lève de fausse alerte sur les runs normaux : le seuil d'alerte est assez haut. Le ML seul prend presque tous les redémarrages "
                f"et la moitié des rafales pour des attaques ; le LLM/RAG les écarte presque tous. Le reste des faux positifs vient presque entièrement de la variante "
                f"<b>maintenance jamais vue</b> ({n(B2['fpr_benign_maintenance_mean'])} pour Baseline 2, {n(EV['fpr_benign_maintenance_mean'])} pour EVA-Guard) : ni la fiche RAG "
                f"disponible ni la règle de confirmation ne la distinguent d'un DoS."),
              KeepTogether([P("11.3 Délais", "h2"), img("times.png", 11, "Figure 5 — Temps de détection et de confirmation (secondes).")]),
              P(f"Le temps de détection est identique pour les trois systèmes (≈ {n(EV['detect_time_s_mean'], 0)} s après le début de l'épisode) car ils partagent la même alerte "
                f"(deux fenêtres consécutives au-dessus du seuil et lissage sur trois fenêtres). La confirmation ajoute {n(EV['confirm_time_s_mean'], 0)} s en médiane : c'est le coût "
                "de la persistance. Un gain de précision aurait pu justifier ce coût ; ici il ne se matérialise pas."),
              KeepTogether([P("11.4 Cas d'étude rejoués (graine 100)", "h2"),
                            img("cases.png", 16, "Figure 6 — Score d'anomalie (gauche) et métriques clés (droite) pour cinq runs : Eclipse et DoS confirmés, rafale et redémarrage écartés, "
                                                 "maintenance non écartée (faux positif d'EVA-Guard).")])]
    for c in cases[:2] + cases[-1:]:
        story += [KeepTogether([P(f"<b>{c['title']}</b> — vérité terrain : {c['run_type']} ; Baseline 1 : {c['baseline1_pred']} ; Baseline 2 : {c['baseline2_pred']} ; "
                                  f"EVA-Guard : {c['eva_pred']}", "small"),
                                Preformatted(c["report"], S["code"], maxLineLength=104)])]

    # ------------------------------------------------------------------ 12. ablation
    order = ["EVA-Guard complet", "sans source RPC", "sans source système", "sans source P2P", "sans LLM/RAG (type ML)", "sans persistance (1 fenêtre)",
             "sans exigence multi-source", "k = 2 indicateurs", "k = 4 indicateurs"]
    story += [P("12. Étude ablative", "h1"),
              P("Chaque variante retire ou modifie un composant d'EVA-Guard, tous les autres paramètres restant ceux sélectionnés sur la validation. Mêmes runs de test."),
              table([["Variante", "Precision", "Recall", "F1", "Faux positifs", "Confirm. (s)"]] +
                    [[k, pm(ab[k]["precision_mean"], ab[k]["precision_std"]), pm(ab[k]["recall_mean"], ab[k]["recall_std"]), pm(ab[k]["f1_mean"], ab[k]["f1_std"]),
                      pm(ab[k]["fpr_mean"], ab[k]["fpr_std"]), n(ab[k]["confirm_time_s_mean"], 0)] for k in order],
                    [4.6 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm]),
              Spacer(1, 4), img("ablation.png", 15.5, "Figure 7 — F1 et taux de faux positifs par variante (moyenne ± écart-type)."),
              P("<b>Ce que l'ablation montre :</b>"),
              *bullets([f"<b>Le LLM/RAG est le composant qui réduit les faux positifs</b> : sans lui, la confirmation seule laisse {n(ab['sans LLM/RAG (type ML)']['fpr_mean'])} de faux positifs "
                        f"(contre {n(EV['fpr_mean'])} avec).",
                        f"<b>La persistance n'a pas d'effet sur les faux positifs</b> : sans elle, les faux positifs restent à {n(ab['sans persistance (1 fenêtre)']['fpr_mean'])}, le rappel "
                        f"remonte ({n(ab['sans persistance (1 fenêtre)']['recall_mean'])}) et la confirmation est immédiate. Les épisodes bénins qui franchissent les seuils les "
                        "franchissent assez longtemps.",
                        f"<b>L'exigence multi-sources coûte du rappel sans gain de précision</b> : la retirer donne F1 {n(ab['sans exigence multi-source']['f1_mean'])} à faux positifs identiques.",
                        f"<b>Retirer la source RPC effondre le rappel</b> (F1 {n(ab['sans source RPC']['f1_mean'])}) : le catalogue Eclipse ne contient qu'un indicateur non P2P (le retard de "
                        "synchronisation, source RPC). Sans lui, la contrainte de deux sources ne peut plus être satisfaite pour l'Eclipse. C'est un effet de conception du catalogue, pas "
                        "une propriété générale des sources.",
                        f"<b>k = 4 est trop strict</b> (rappel {n(ab['k = 4 indicateurs']['recall_mean'])}) ; k = 2 et k = 3 sont équivalents ici."])]

    # ------------------------------------------------------------------ 13. discussion
    story += [P("13. Analyse, limites et menaces à la validité", "h1"),
              P("13.1 Pourquoi la confirmation n'améliore pas ML + LLM/RAG ici", "h2"),
              P("Ce sont des <b>hypothèses d'explication</b>, cohérentes avec l'ablation mais non testées isolément :"),
              *bullets(["<b>Les « sources » ne sont pas indépendantes.</b> Dans le simulateur comme sans doute en réalité, un pic de charge (légitime ou non) fait monter ensemble messages, "
                        "CPU, latence et erreurs. Trois sources qui réagissent à la même cause ne fournissent pas trois preuves indépendantes de l'<i>intention</i> malveillante.",
                        "<b>Les seuils sont appris sur le normal seulement.</b> Tout épisode bénin intense dépasse le percentile 99 de la baseline, quel que soit son origine. "
                        "Le catalogue vérifie « est-ce anormal ? », pas « est-ce anormal <i>d'une manière propre à l'attaque</i> ? ».",
                        "<b>Le LLM/RAG utilise déjà le même signal.</b> L'agent d'interprétation voit les mêmes métriques que la corrélation ; la confirmation répète en partie son raisonnement.",
                        "<b>La règle est sélectionnée sans variante inattendue.</b> La validation ne contient ni maintenance ni autre comportement bénin inédit ; la règle optimale pour ces données est donc laxiste."]),
              P("13.2 Limites de l'étude", "h2"),
              *bullets(["<b>Données simulées.</b> Les profils sont des modèles simplifiés des symptômes décrits dans le cahier des charges ; leurs recouvrements (attaques faibles vs charge forte) "
                        "sont des choix de l'auteur. Les chiffres absolus n'ont pas de valeur prédictive sur de vrais nœuds.",
                        "<b>Interprète offline.</b> Fiches et simulateur ont le même auteur ; l'interprète n'est pas un vrai LLM. L'interprète Mistral n'a pas été évalué.",
                        "<b>Un épisode par run, une alerte par run.</b> Pas de multi-incidents, pas de dérive lente de la baseline, pas de chevauchement d'épisodes.",
                        "<b>Cinq graines</b> donnent une idée de la variance de génération, pas de la variance d'expériences réelles.",
                        "<b>Traces réelles limitées au comportement bénin</b> d'un nœud Geth unique (voir 13.4) : aucune attaque réelle n'a été enregistrée, le rappel n'est donc mesuré que sur le simulateur.",
                        "<b>Sélection de paramètres sur validation simulée</b> : la règle (k, sources, persistance) risque de ne pas se transférer."]),
              P("13.3 Expériences qui permettraient de trancher", "h2"),
              *bullets(["Refaire l'évaluation avec des traces réelles (réseau privé instrumenté ou jeux de données des articles) et des épisodes bénins réels variés.",
                        "Ajouter des <b>contre-preuves</b> au catalogue : indicateurs dont la <i>présence</i> exclut l'attaque (ex. : diversité des pairs normale pendant un retard de synchronisation → redémarrage).",
                        "Utiliser une <b>source réellement indépendante</b> : un second nœud observateur, ou la comparaison de la tête de chaîne avec une source externe pour l'Eclipse.",
                        "Apprendre la règle avec une <b>fonction de coût asymétrique</b> (une fausse alerte coûte plus qu'un retard) et sur des bénins plus diversifiés.",
                        "Évaluer l'interprète Mistral et comparer à l'interprète offline sur les mêmes runs."])]

    # ------------------------------------------------------------------ 13.4 réel
    rc = RES / "runs" / "real_check.csv"
    if rc.exists():
        r = pd.read_csv(rc)
        nm = {"normal": "Normal (test)", "benign_restart": "Redémarrage bénin", "benign_burst": "Rafale légitime"}
        rows = [["Système", "Type de run", "Runs", "Classés attaque", "Taux"]]
        for x in r.itertuples():
            rows.append([x.system, nm.get(x.run_type, x.run_type), str(x.runs), str(x.classes_attaque), f"{x.taux:.2f}"])
        story += [P("13.4 Validation sur traces réelles de comportement bénin", "h2"),
                  P("Des runs réels (collecteur RPC + métriques Prometheus + <i>docker stats</i>, fenêtres de 10 s) ont été enregistrés sur un nœud Geth unique en mode <i>--dev</i>, sous quatre "
                    "profils légitimes : repos, charge modérée, charge élevée, et deux épisodes bénins (redémarrage du conteneur, rafale de transferts de faible valeur). "
                    "Les baselines et l'Isolation Forest sont appris sur une partie des runs normaux ; le seuil est le quantile 99,5 % des scores d'entraînement. "
                    "Le tableau donne la part de runs classés « attaque » : <b>toute alerte y est une fausse alerte</b>."),
                  table(rows, [5.2 * cm, 4.2 * cm, 1.8 * cm, 3.0 * cm, 1.8 * cm], align_right_from=2), Spacer(1, 4),
                  P("<b>Lecture prudente.</b> Aucun des trois systèmes n'a produit de fausse alerte, mais cette expérience <b>ne départage pas</b> les systèmes et <b>ne mesure pas le rappel</b> : "
                    "aucune attaque réelle n'a été enregistrée (ces épisodes ne peuvent être produits que dans un environnement isolé et selon la méthode validée par l'encadrant). "
                    "Un taux de 0 sur 3 runs reste compatible avec un taux réel élevé (l'intervalle de confiance à 95 % de Clopper-Pearson va jusqu'à environ 71 %). "
                    "Limites : nœud unique sans pairs (les features de topologie P2P sont constantes), compteurs <i>msgs_in</i> et <i>single_source_ratio</i> non collectés et retirés du modèle, "
                    "épisodes bénins probablement plus doux que ceux d'un réseau réel, effectifs de 3 à 4 runs par type.", "box")]

    # ------------------------------------------------------------------ 13.5 méthode étape C
    story += [P("13.5 Méthode retenue pour les épisodes offensifs", "h2"),
              P("L'encadrant a laissé le choix de la méthode pour les épisodes d'attaque. Nous avons retenu une méthode <b>sans exécution d'attaque réelle</b>, en trois volets complémentaires :"),
              *bullets(["<b>Émulation au niveau des métriques.</b> Le simulateur produit des séries de métriques (aucun paquet, aucun trafic) où un épisode Eclipse ou DoS P2P déforme les 12 métriques selon un profil documenté. "
                        "Un paramètre d'intensité (0,1 à 1,0) permet une <b>étude de sensibilité</b> : à partir de quelle amplitude chaque système détecte l'épisode (figure du rapport technique, section 7.3).",
                        "<b>Import de traces autorisées.</b> Le dashboard et <i>real_check</i> acceptent des traces au format du collecteur ; si l'encadrant ou une source publique fournit des traces d'attaque, elles s'ajoutent au manifeste (<i>eclipse</i>, <i>dos_p2p</i>) et le rappel réel se mesure sans modifier le code.",
                        "<b>Vue « chemin observé ».</b> Pour chaque incident, le dashboard reconstruit l'ordre dans lequel les effets mesurables sont apparus (voisinage, connexions, synchronisation ; ou trafic, ressources, service). C'est une lecture défensive des symptômes, pas une description de la méthode d'un attaquant."]),
              P("<b>Ce que cette méthode ne permet pas.</b> Elle ne prouve pas que les systèmes détectent de vraies attaques : les profils sont écrits par les auteurs. Elle permet en revanche de comparer les systèmes entre eux, de repérer la zone grise des attaques faibles "
                "et de préparer l'évaluation réelle dès que des traces seront disponibles.", "box"),
              img("sensitivity.png", 15.5, "Figure 13.5 — Part des épisodes simulés détectés selon l'intensité (3 graines × 12 runs par niveau)."),
              ]

    # ------------------------------------------------------------------ 14. dashboard/usage
    story += [P("14. Dashboard, utilisation et reproductibilité", "h1"),
              P("<b>Dashboard.</b> Deux versions : <i>dashboard/app.py</i> (Streamlit, rejeu interactif avec curseur de fenêtre : courbes, alerte, hypothèse et fiches citées, tableau de preuves, "
                "décision, rapport) et <i>dashboard/dashboard.html</i> (page autonome sans serveur, cinq cas rejoués). L'application Streamlit a été exécutée en test automatisé sur les cinq cas, sans erreur."),
              P("<b>Commandes.</b>"),
              Preformatted("pip install -r requirements.txt\n"
                           "python -m pytest -q tests                  # 8 tests unitaires\n"
                           "python run_all.py                          # évaluation (5 graines, ~20 min) + figures + dashboard + PDF\n"
                           "python run_all.py --figures                # régénère figures, dashboard et PDF depuis results/\n"
                           "streamlit run dashboard/app.py             # dashboard interactif\n"
                           "python collectors/collector.py --rpc http://127.0.0.1:8545 --out results/real_run.csv --duration 3600", S["code"]),
              P("<b>Étapes pour passer à des données réelles.</b>"),
              *bullets(["Lancer le réseau privé (infra/network_params.yaml) et vérifier les métriques Prometheus ; adapter les noms de paramètres à la version de l'ethereum-package.",
                        "Enregistrer des runs normaux avec le collecteur (au moins 24 h cumulées, trois profils de charge) et des épisodes bénins (redémarrage, rafale).",
                        "Obtenir de l'encadrant la méthode et les traces autorisées pour les épisodes offensifs, puis étiqueter par run (colonnes run_type, onset, event_end).",
                        "Brancher ces CSV à la place du simulateur dans eva_guard/evaluate.py (même schéma de colonnes) et relancer l'évaluation.",
                        "Activer l'interprète Mistral (variable MISTRAL_API_KEY) et comparer."])]

    # ------------------------------------------------------------------ 15. répartition
    story += [P("15. Répartition du travail à quatre", "h1"),
              P("Proposition de répartition pour l'équipe (à ajuster entre vous) : trois rôles techniques et un rôle de bibliographie, rapport, intégration et démonstration."),
              table([["Membre (proposé)", "Rôle", "Responsabilités", "Livrables dans le dépôt"],
                     ["Hadil Kharoubi", "Infrastructure et données", "Réseau Ethereum privé, monitoring, collecteur, baseline normale, runs étiquetés, documentation du dataset, agent de corrélation (requêtes Prometheus/RPC).",
                      "infra/, collectors/, dataset documenté, agents.py (CorrelationAgent)"],
                     ["Baya Sayah", "ML et évaluation", "Features, détection (Isolation Forest, Random Forest), seuils, protocole d'évaluation, métriques, ablation, intervalles de confiance.",
                      "features.py, detector.py, evaluate.py, tableaux et figures"],
                     ["Mohamed Amine Gharbi", "LLM, agents et dashboard", "Base RAG, interprète (offline et Mistral), agent de confirmation et restitution, pipeline, dashboard.",
                      "knowledge/, rag.py, llm.py, agents.py, dashboard/"],
                     ["Hedi Gouia", "Bibliographie, rapport, intégration, démo", "Synthèse des trois articles, rédaction et mise à jour du rapport, tests d'intégration (pytest, Docker), scénario de démonstration, préparation de la soutenance.",
                      "report/, tests/, Dockerfile, docker-compose.yml, README.md"]],
                    [2.9 * cm, 2.9 * cm, 7.0 * cm, 4.0 * cm]),
              Spacer(1, 6),
              P("Tous les membres lisent au moins un article, participent à l'intégration (semaines 13-14) et à la soutenance. Les contrats JSON "
                "(eva_guard/schemas.py) sont le point de synchronisation : ils se figent en semaine 2 et permettent le travail en parallèle.")]

    # ------------------------------------------------------------------ 16. conclusion
    story += [P("16. Conclusion et perspectives", "h1"),
              P("Le prototype EVA-Guard démontre de bout en bout la chaîne observation → détection → hypothèse → preuves → confirmation → explication, avec des agents "
                "aux contrats clairs, une règle de confirmation explicite, un banc d'essai reproductible et un dashboard. Sur télémétrie simulée, l'apport mesurable vient du "
                "contexte LLM/RAG (faux positifs de " + n(B1['fpr_mean']) + " à " + n(B2['fpr_mean']) + "), pas de la confirmation multi-sources, qui n'améliore pas la Baseline 2 et allonge le délai de décision."),
              P("Ce résultat négatif est utile : il montre que la valeur de la confirmation dépend de l'<b>indépendance réelle des preuves</b> et de la présence de <b>contre-preuves</b>, "
                "pas seulement de leur nombre. Les prochaines étapes, dans l'ordre : données réelles, contre-preuves dans le catalogue, source d'observation indépendante, "
                "évaluation de l'interprète Mistral, puis extension au scénario optionnel (RPC flooding)."),
              P("Sources : cahier des charges du mini-projet EVA-Guard (matière Blockchain) ; documentation Geth, Prometheus et Kurtosis ethereum-package ; scikit-learn. "
                "Références des trois articles imposés : voir section 3.", "small")]

    doc = Doc(str(OUT))
    doc.multiBuild(story)
    print("écrit", OUT)


if __name__ == "__main__":
    main()
