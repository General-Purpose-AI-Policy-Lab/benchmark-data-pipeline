# Fusion des pipelines de données : diagnostic, désidérata, état d'avancement

Rédigé le 2026-09-04 après lecture complète de `Multiaxis_ECI/1_data/`, `eval-data-pipeline/` (devenu ce dépôt) et `Model_Benchmark_forecasting/0_Process_benchmarks.ipynb`. Mis à jour le 2026-09-07 : la section 3 décrit ce qui est fait et ce qui reste, les décisions détaillées sont dans `decisions.md`.

## 1. Diagnostic : ce que faisaient les trois pipelines

### 1.1 Les trois implémentations de la même chose

| | Multiaxis_ECI `1_data/1_pipeline/pipeline.ipynb` | eval-data-pipeline `pipeline.ipynb` + `helpers.py` | Model_Benchmark_forecasting `0_Process_benchmarks.ipynb` |
|---|---|---|---|
| Taille | 1 431 lignes de code, 32 cellules | 466 lignes + 8 Ko de helpers + 5 Ko `refresh.py` | 3 997 lignes, 45 cellules |
| Fetch | dans le notebook, snapshots datés + provenance | `refresh.py` séparé, `input/feed/` versionné, `provenance.json` | `refresh_epoch_data.py` (parse le source du notebook par regex) + Scale scrapé en live avec Playwright, sans cache |
| Sources | Epoch ZIP, Epoch live, RAND, SEAL, Kaggle | idem, hors-ligne | Epoch (CSV committés), SEAL (Playwright, 3 parseurs de repli), RAND local |
| Identité modèle | chaîne plate `model_version` + `model_aliases.csv` 390 lignes | tuple `(base_model, reasoning_level, reasoning_tokens, snapshot, variant)`, uuid5, grammaire `split_name`, un `aliases.csv` par source | aucune : les chaînes brutes coexistent, dédoublonnage par clé texte |
| Dates de sortie | Epoch ; SEAL/RAND/Kaggle non datés (1 108 lignes sur 5 064) ; `config.RELEASE_DATES` en dur | modale Epoch par `model_id` ; 103 modèles non datés | `MANUAL_DATE_MAP` (~400 entrées), `DATE_OVERRIDES` |
| Organisation / pays | `VENDOR_CANON` + vote modal + overrides ; `4_build_country_map.py` (US/CN/Other) | `organizations.csv` (100 blancs / 536), pays en clair | regex sur le nom |
| Planchers / catégories / baselines | trois CSV curés, baselines réécrites par le notebook | trois CSV identiques, baselines jamais émises | tables dans le notebook, 7 planchers et 14 catégories divergents, 62 baselines |
| Exclusions et fusions | `FILE_SKIP`, `retired_benchmarks.txt`, `excluded_benchmarks.txt` au fit | `FILE_SKIP` seulement | `EXCLUDED_CSV_FILES`, `MANUALLY_EXCLUDED_BENCHMARKS` dans les données ; SWE Atlas ×3 et PRBench ×2 fusionnés |
| Sortie | 1 CSV plat 8 colonnes, 100 benchmarks, 835 modèles, 5 064 lignes | 3 CSV liés par uuid, 100 benchmarks, 930 modèles, 5 437 scores | 1 CSV plat + `lower_bound` + `category`, 75 benchmarks, 4 612 lignes |

### 1.2 Divergences de fond mesurées le 2026-09-04

Noms de benchmarks différents pour le même objet (`Blueprint-Bench 2` / `BlueprintBench 2`, `OSWorld 2.0` / `OS World 2`, `CommonsenseQA 2.0` / `CSQA2`, PRBench fusionné ou non). Sept planchers divergents (Chess Puzzles, HLE, METR, Mystery Game Puzzles, TriviaQA, SimpleBench, SpatialViz-Bench). Deux vocabulaires de catégories et 14 benchmarks classés différemment. Trois fichiers de baselines humaines pour un fait, 21 lignes divergentes. 54 modèles avec au moins deux dates de sortie selon la source. Tout cela est tranché, ligne par ligne, dans `decisions.md`.

### 1.3 Ce que les consommateurs lisent réellement

`multiaxis_eci/data.py` : `model_version, score, benchmark, stderr, category, release_date, organization` plus des fichiers curés (planchers, clips, exclusions, baselines, lignée, pays). `forecasting.py` (MBF) : `benchmark, release_date` (obligatoire), `score, lower_bound, category`, et `model_version` pour le dédoublonnage. Intersection : scores en [0,1], identité modèle stable, date de sortie, plancher, catégorie, baselines humaines. Tout le reste est du choix de modélisation.

## 2. Désidérata et leur état

Numérotés pour pouvoir y référer depuis les revues. État au 2026-09-07 : **fait**, **partiel**, **à faire**.

| | Désidératum | État |
|---|---|---|
| D1 | Chaque fait (nom canonique, plancher, catégorie, accès, alias, date, organisation, baseline) vit dans un fichier, dans un dépôt | **fait** côté pipeline (`0_input/metadata/`, `aliases.csv` par source) ; les deux repos de modélisation gardent leurs tables jusqu'à la phase 5 |
| D2 | Chaque ligne curée porte raison et source | **fait** pour planchers, plafonds, accès, dates, baselines, alias (colonne `note`) |
| D3 | Rien de silencieux : tout élément amont est ingéré, écarté avec raison, ou signalé | **fait** (`_SPEC` / `_SKIP`, noms non résolus, restes des jointures, benchmarks exclus comptés) |
| D4 | `build_report.md` et diff vs build précédent | **partiel** : le build logue tout et signale les modèles nouveaux ; pas de fichier de rapport ni de diff persistant |
| D5 | Identité structurée, vide = inconnu, uuid5 | **fait** ; le harness est resté hors du tuple (décision A3 : meilleur score toutes harness confondues, harness porté par le score) |
| D6 | Une fonction unique dérive `model_version` depuis le tuple | **fait** (`identity.machine_name` ; la graphie observée chez Epoch ou Kaggle l'emporte) |
| D7 | Table `model_names.csv` de toutes les graphies vues | **à faire** (les graphies sont comptées au build, non exportées) |
| D8 | Quatre couches de décision séparées : source, identité, validité, périmètre | **fait**, le périmètre étant tranché dans `benchmarks.csv` (`status`) plutôt que chez les consommateurs (décision A5) |
| D9 | Un benchmark retiré reste dans la base avec un statut | **partiel** : le statut vit dans `benchmarks.csv`, les scores des benchmarks exclus sont écartés à l'ingestion |
| D10 | `score_raw` et `transform` réversibles | **à faire** (les diviseurs sont dans les `_SPEC`, pas dans la table) |
| D11 | Build hors-ligne et déterministe | **fait** (test golden, double build) |
| D12 | Provenance par artefact et `build_manifest.json` | **partiel** : `provenance.json` existe, pas de manifeste de build |
| D13 | Golden et parité avec les deux consommateurs, écarts documentés | **fait** (`python -m benchmark_data parity`, écarts par cause) |
| D14 | Paquet Python, style Google, ruff, pytest | **fait** (72 tests, ruff propre) ; pas de CI |
| D15 | CLI `refresh`, `build`, `check`, `diff` | **fait** avec `parity` à la place de `diff` |
| D16 | Ajouter une source = un module, une spec, un `aliases.csv` | **fait** |
| D17 | Aucune boucle `iterrows` | **fait** |
| D18 | Tables normalisées versionnées et deux vues documentées | **fait** (schéma 2.1, `3_views/`) |
| D19 | Colonnes complètes sur `scores`, `benchmarks`, `models` | **partiel** : `source_label`, `source_url`, `model_version`, `ceiling`, `access` faits ; `score_raw`, `transform`, `measurement_date`, `task_version`, `n_items`, `tier` non |
| D20 | Métadonnées complètes : catégorie, plancher, accès pour 100 % des benchmarks, ≥ 95 % des scores sur un modèle daté | **fait** : 100 % des benchmarks inclus ; 2 modèles non datés par décision ; toutes les organisations renseignées |
| D21 | Pages SEAL non redistribuées, `NOTICE.md` | **fait** |

## 3. Plan : fait et reste à faire

### 3.1 Architecture retenue

Le pipeline commun est construit sur les fondations d'`eval-data-pipeline` (identité structurée, alias par source, déterminisme, feed versionné), renommé `benchmark-data-pipeline`. Il porte les sources et benchmarks supplémentaires de MBF, les planchers et catégories arbitrés, les baselines humaines réconciliées, et produit les tables et les vues. Les consommateurs gardent ce qui est un choix de modélisation : lignée et SOTA (Multiaxis), top-N et asymptotes fixées (MBF), bucketisation US/CN/Other.

### 3.2 Arborescence, dans l'ordre du traitement

```
benchmark-data-pipeline/
├── 0_input/
│   ├── feed/<source>/              brut versionné + aliases.csv par source ; provenance.json ; SEAL gitignoré
│   └── metadata/                   benchmarks.csv, organizations.csv, release_dates.csv, sibling_merges.csv, human_baselines.csv
├── 1_pipeline/benchmark_data/      le paquet : identity, sources/, steps/, views/, build, check, parity, refresh
├── 2_database/                     models.csv, benchmarks.csv, scores.csv, human_baselines.csv
├── 3_views/                        all_scores_flat.csv, dated_scores_flat.csv, human_baselines.csv
├── docs/                           decisions.md, decisions_pending.md, plan_fusion.md
├── tests/                          unitaires, golden (expected_database, expected_views), parité (golden des consommateurs)
└── notebooks/tour.ipynb            lecture seule
```

### 3.3 Ordre d'un build

```
0_input/feed/<source>/         brut, versionné, provenance
  │  sources/<source>.translate()     couche source : fichier, colonne, diviseur, source_label, source_url
  ▼
records                        raw_name, benchmark, score, stderr, effort, harness, meta, source
  │  steps/ingest                     périmètre (benchmarks.csv status) puis identité (aliases puis grammaire) ; non résolus signalés
  │  steps/dedup                      doublons exacts puis max ; désaccords signalés
  │  steps/merge_siblings             PRBench, SWE Atlas
  ▼
scores                         une ligne par (model_id, benchmark_id)
  │  steps/enrich                     model_version ; organisations (fichier puis Epoch) ; dates (Epoch modale, Epoch model_metadata, release_dates.csv, frères) ; benchmarks.csv
  │  steps/human_baselines            copie contrôlée
  │  steps/validate                   invariants
  ▼
2_database/ + 3_views/         export trié, déterministe ; check contre les copies bénies ; parity contre les consommateurs
```

### 3.4 Phases

| Phase | Contenu | État |
|---|---|---|
| 0 | Geler les sorties des consommateurs (`tests/parity/golden/`, commits 55687ce et 2ed2c34) | **fait** 2026-09-04 |
| 1 | Sortir le code du notebook en paquet, golden identique | **fait** 2026-09-04 |
| 2 | Config hors du code, `benchmarks.csv` unifié, harness, fusions de frères, périmètre à l'ingestion, anglais | **fait** 2026-09-04 |
| 3 | Réconcilier planchers, catégories, noms, baselines humaines, dates de sortie, organisations ; exporter les baselines | **fait** du 2026-09-04 au 07 (onze lots de décisions, `decisions.md`) |
| 4 | Vues consommateurs, `model_version`, parité par cause | **fait** 2026-09-07 |
| 5 | Basculer les consommateurs : Multiaxis lit `all_scores_flat.csv` et `human_baselines.csv`, supprime son pipeline, `config.RELEASE_DATES` et les CSV curés migrés ; MBF charge `dated_scores_flat.csv`, supprime `MANUAL_DATE_MAP`, `DATE_OVERRIDES`, `refresh_epoch_data.py` et le scraper. Critère : les fits canoniques se relancent à la tolérance MCMC | **à faire**, sur décision |
| 6 | Hygiène : CI (ruff, pytest, golden avec une fixture SEAL réduite), `build_manifest.json`, `model_names.csv`, `score_raw` / `transform`, rapport et diff de build persistants, cron de rafraîchissement | **à faire** |

Ce qui a changé par rapport au plan initial : le harness n'est pas entré dans le tuple d'identité (A3) ; le périmètre est tranché dans le pipeline et non chez les consommateurs (A5) ; les benchmarks exclus ne sont pas écrits dans la base ; la vue « forecasting » s'appelle `dated_scores_flat.csv` et les deux vues portent plancher et plafond ; les dossiers sont numérotés dans l'ordre du traitement.
