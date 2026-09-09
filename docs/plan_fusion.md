# Fusion des pipelines de données : diagnostic, désidérata, état d'avancement

Rédigé le 2026-09-04 après lecture complète de `Multiaxis_ECI/1_data/`, `eval-data-pipeline/` (devenu `benchmark-data-pipeline`) et `Model_Benchmark_forecasting/0_Process_benchmarks.ipynb`. Mis à jour le 2026-09-09 : les phases 0 à 5 sont faites, les deux dépôts de modélisation consomment les vues du pipeline et partagent la même organisation ; la section 4 liste ce qui reste et ce qui mérite encore une décision. Les décisions détaillées sont dans `benchmark-data-pipeline/docs/decisions.md` ; ce fichier est recopié dans `benchmark-data-pipeline/docs/plan_fusion.md`.

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

Numérotés pour pouvoir y référer depuis les revues. État au 2026-09-09 : **fait**, **partiel**, **abandonné** (sur décision), **à faire**.

| | Désidératum | État |
|---|---|---|
| D1 | Chaque fait (nom canonique, plancher, catégorie, accès, alias, date, organisation, baseline) vit dans un fichier, dans un dépôt | **fait** : `0_input/metadata/` et un `aliases.csv` par source dans le pipeline ; les deux dépôts de modélisation ne gardent que leurs choix de modélisation (`1_curated/` chez MX : exclusions, lignée, SOTA, clips ; `config.EXCLUDED_BENCHMARKS` vide chez MBF) |
| D2 | Chaque ligne curée porte raison et source | **fait** pour planchers, plafonds, accès, dates, baselines, alias (colonne `note`) |
| D3 | Rien de silencieux | **fait** : `_SPEC` / `_SKIP`, noms non résolus, restes des jointures, `excluded_benchmarks.csv`, scores sous le plancher journalisés |
| D4 | `build_report.md` et diff vs build précédent | **partiel** : le build journalise tout, `parity` écrit `reports/parity_<consommateur>.md`, le workflow mensuel joint ces rapports à sa PR ; pas de diff persistant entre deux builds (le diff git de la PR en tient lieu) |
| D5 | Identité structurée, vide = inconnu, uuid5 | **fait** ; le harness reste hors du tuple (A3 : meilleur score toutes harness confondues, harness porté par le score) |
| D6 | Une fonction unique dérive `model_version` depuis le tuple | **fait** (`identity.machine_name` ; la graphie observée chez Epoch ou Kaggle l'emporte) |
| D7 | Table `model_names.csv` de toutes les graphies vues | **fait** (`2_database/model_names.csv`) |
| D8 | Quatre couches de décision séparées | **fait**, le périmètre étant tranché dans `benchmarks.csv` (`status`, `exclusion_criterion`) plutôt que chez les consommateurs (A5) |
| D9 | Un benchmark retiré reste dans la base avec un statut | **abandonné** (A5) : le statut vit dans `benchmarks.csv`, les scores exclus sont écartés à l'ingestion et comptés dans `excluded_benchmarks.csv` |
| D10 | `score_raw` et `transform` réversibles | **abandonné** (décision du 2026-09-07) : les diviseurs restent dans les `_SPEC` |
| D11 | Build hors-ligne et déterministe | **fait** (golden, double build) |
| D12 | Provenance par artefact et `build_manifest.json` | **fait** (`0_input/feed/provenance.json`, `2_database/build_manifest.json` : schéma, commit, hachages des entrées, comptes) |
| D13 | Golden et parité avec les deux consommateurs | **fait** (`python -m benchmark_data parity`, écarts par cause) |
| D14 | Paquet Python, style Google, ruff, pytest, CI | **fait** (`ci.yml` ruff + pytest) |
| D15 | CLI `refresh`, `build`, `check`, `diff` | **fait** avec `parity` à la place de `diff` |
| D16 | Ajouter une source = un module, une spec, un `aliases.csv` | **fait** (sept feeds : epoch, epoch_live, epoch_cyber, cybench_site, kaggle, rand, seal) |
| D17 | Aucune boucle `iterrows` | **fait** |
| D18 | Tables normalisées versionnées et vues documentées | **fait** (schéma 2.1 ; `3_views/all_scores_flat.csv`, `dated_scores_flat.csv`, `human_baselines.csv`) |
| D19 | Colonnes complètes | **fait** pour ce qui a été retenu (`source_label`, `source_url`, `model_version`, `ceiling`, `access`, `country` ISO, `training_flop`) ; `score_raw`, `transform`, `measurement_date`, `task_version`, `n_items`, `tier` abandonnés (2026-09-07) |
| D20 | Métadonnées complètes | **fait** : 100 % des benchmarks inclus avec catégorie, plancher et accès ; 2 modèles non datés par décision ; toutes les organisations renseignées |
| D21 | Pages SEAL non redistribuées, `NOTICE.md` | **fait** |

## 3. Plan : fait et reste à faire

### 3.1 Architecture retenue

Le pipeline commun est construit sur les fondations d'`eval-data-pipeline`, renommé `benchmark-data-pipeline`. Il porte toutes les sources, les planchers et catégories arbitrés, les baselines humaines réconciliées, les dates de sortie recherchées, et produit les tables et les vues. Les consommateurs gardent ce qui est un choix de modélisation : lignée, SOTA, exclusions « faciles pour les humains », familles isolées, bucketisation US/CN/Other (Multiaxis) ; top-N, règles d'asymptote, cutoff (MBF).

### 3.2 Organisation commune des trois dépôts (2026-09-08 et 09)

Les trois dépôts lisent dans l'ordre du traitement, avec des dossiers numérotés uniquement (GitHub liste les dossiers avant les fichiers), une génération de données en tête de chaque sortie, les figures anglaises par défaut avec un sous-dossier `fr/`, et aucun chemin personnel dans un fichier suivi (`provenance.json` enregistre le remote git du pipeline).

```
benchmark-data-pipeline/     0_input/{feed, metadata}  1_pipeline/benchmark_data  2_database/  3_views/  docs/  tests/
Multiaxis_ECI/               0_input/  1_curated/  2_model/multiaxis_eci  3_fit/fit.py  4_diagnostics/
                             5_outputs/data<YYYYMMDD>/{<fit>/ (tables, trace, figures/ + html/ + fr/), comparisons/, diagnostics/}
                             5_outputs/pre_pipeline/ (fits publiés)  6_writeups/{blogpost, us_cn_frontier, dashboard}  archive/  internal_evals/
Model_Benchmark_forecasting/ 0_input/  1_model/benchmark_forecasting  2_analyses/{forecasts.py, revision_analyses.py}
                             3_outputs/cutoff<YYYYMMDD>/{fits, forecasts (+fr), calibration (+fr), sensitivity, high_level}  4_writeups/{paper, note}  archive/
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
  │  steps/enrich                     model_version ; organisations ; dates (Epoch modale, Epoch model_metadata, release_dates.csv, frères) ; benchmarks.csv
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
| 3 | Réconcilier planchers, catégories, noms, baselines humaines, dates de sortie, organisations | **fait** du 2026-09-04 au 07 (onze lots de décisions) |
| 4 | Vues consommateurs, `model_version`, parité par cause | **fait** 2026-09-07 |
| 5 | Basculer les consommateurs | **fait** 2026-09-07 à 09. MBF : paquet `1_model/benchmark_forecasting`, `0_input/` synchronisé, notebook 0, `Data/`, `refresh_epoch_data.py` et le scraper supprimés, règle d'asymptote unifiée (`L_floor_observed`, `L_fixed_from_ceiling`), catégorie Cyber, analyses relancées. Multiaxis : `0_input/` synchronisé, `1_curated/` réduit aux choix de modélisation, `1_data/`, `config.RELEASE_DATES`, la regex d'effort et `--cyber` supprimés, identité lue dans `models.csv`, familles isolées écartées, prior ordonné sur les humains, goldens re-bénis ; canoniques relancés sur la génération 2026-09-08 (convergés), K=4 en cours |
| 6 | Hygiène continue | **partiel** : CI ruff + pytest et rafraîchissement mensuel avec PR côté pipeline (`ci.yml`, `refresh.yml`), `build_manifest.json`, `model_names.csv`, `excluded_benchmarks.csv`, `decisions.md` tenu à jour ; pas de CI dans les deux dépôts de modélisation, pas de runbooks séparés (le README de chaque dépôt en tient lieu) |

Ce qui a changé par rapport au plan initial : le harness n'est pas entré dans le tuple d'identité (A3) ; le périmètre est tranché dans le pipeline (A5) ; les benchmarks exclus ne sont pas écrits dans la base ; `score_raw`, `transform`, `measurement_date`, `task_version`, `n_items`, `tier` ont été abandonnés ; pas de notebook de visite (le README documente) ; les dossiers sont numérotés dans l'ordre du traitement dans les trois dépôts.

## 4. Ce qui reste

### 4.1 Décisions en attente (utilisateur)

- **Échelle humaine de Multiaxis sur les nouvelles données.** Top Performer repose sur le score parfait d'EBR-bench (1,000), ce qui le porte à ECI 204 et repousse son franchissement de mai 2025 à juin 2027 ; Average Human ne tient plus qu'à MMLU (34,5 %), TriviaQA et EBR-bench ; Committee of Average Humans n'a plus aucun benchmark dans le périmètre (ARC-AGI, HellaSwag, WinoGrande, OpenBookQA exclus par `1_curated/excluded_benchmarks.txt`). Retirer ou borner la ligne EBR, ou accepter.
- **Catégorie de NL2Bash** (Cyber, provisoire).
- **Sort des traces publiées avant le pipeline** (`5_outputs/pre_pipeline/`, 21 Go, non régénérables sans les anciennes données) une fois les nouveaux résultats validés.
- **`lineage_map.csv` régénéré** (699 lignes changées) et `benchmark_score_clips.csv` à relire ; la liste SOTA est désormais calculée par familles depuis le fit canonique (2026-09-09), plus rien à relire de ce côté.
- **Métadonnées orphelines** signalées par le build (`Aria`, `ByteVideoLLM-14B`) : alias manquant ou lignes à retirer d'`organizations.csv`.

### 4.2 Travail restant

- Multiaxis : fin du K=4 sur la génération 2026-09-08 et déplacement de son dossier dans `5_outputs/` ; régénération des figures des deux canoniques et de la frontière pays avec le nouveau code (`--skip-sampling`) ; tests lents ; `--censor-bounds` diverge encore (plancher dur du log-vraisemblance), à corriger seulement si le mode censuré est voulu ; `index.html` et les figures du billet restent ceux des données d'avant pipeline.
- MBF : relancer `2_analyses/forecasts.py` (les caches ne correspondent plus aux données resynchronisées après les corrections d'alias) puis `revision_analyses.py`.
- Pousser les trois dépôts (pipeline après `a5770d1`, Multiaxis et MBF jamais poussés depuis la restructuration).
- Phase 6 : CI ruff + pytest dans Multiaxis et MBF (le pipeline en a) ; diff persistant entre deux builds si la PR mensuelle ne suffit pas à la relecture.
