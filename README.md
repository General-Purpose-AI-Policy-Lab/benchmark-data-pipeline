# eval-data-pipeline

Transforme des feeds de scores d'évals (Epoch, Kaggle, RAND, Scale SEAL) en trois CSV liés par UUID :
`database/scores.csv`, `database/models.csv`, `database/benchmarks.csv`.

## Arborescence

```
pipeline.ipynb          lit les feeds, résout les noms, écrit database/. Run All = tout.
helpers.py              découpe des noms machine, aliases, uuid5.
input/feed/<source>/    données brutes d'une source + son aliases.csv (un par source, jamais partagé).
input/metadata/         sources de la passe metadata. 
database/               outputs.
```

Feeds présents : `epoch` (76 CSV du ZIP Epoch), `epoch_live` (1 CSV), `kaggle` (3 JSON),
`rand` (1 CSV), `seal` (14 HTML). Snapshot local, rafraîchi par `refresh.py` (voir « Lancer ») ;
dates et sha256 dans `input/feed/provenance.json`.

**Les pages SEAL ne sont pas versionnées.** Scale AI ne publie ses leaderboards sous
aucune licence ouverte, donc `input/feed/seal/*.html` est gitignoré (cf. `NOTICE.md`).
Sur un clone frais, lancer `python3 refresh.py` **avant** le Run All — sinon le notebook
s'arrête avec un message explicite. Le reste du feed SEAL (aliases, sha256, scores
dérivés dans `database/`) reste versionné.

## Les trois CSV

### models.csv

| colonne | rôle |
|---|---|
| `model_id` | uuid5 du tuple d'identification. Clé primaire. |
| `base_model`, `reasoning_level`, `reasoning_tokens`, `snapshot`, `variant` | **identification** — entrent dans l'ID |
| `organization`, `country`, `publication_date`, `training_flop` | **metadata** — n'entrent PAS dans l'ID |

Ajouter une colonne metadata ne change aucun ID. Corriger une colonne d'identification en change un.

### benchmarks.csv

| colonne | rôle |
|---|---|
| `benchmark_id` | uuid5 du `name`. Clé primaire. |
| `name` | identification (seule colonne dans l'ID) |
| `category`, `floor`, `access` | metadata (`floor` vient de `lower_bound` dans `floors.csv` ; `access` ∈ public / semi_private / private / dynamic, depuis `input/metadata/access.csv`) |

Les colonnes de justification (`notes`, `reason`, `source_url`) restent dans `input/metadata/`.

### scores.csv

`model_id`, `benchmark_id`, `score`, `stderr`, `feed`. Une ligne par `(model_id, benchmark_id)` ;
`stderr` vide quand la source ne la publie pas.

## Conventions (non négociables)

- **Case vide = unknown.** `unknown ≠ known` : `opus-5` (level vide) et `opus-5_high` (level `high`)
  sont deux modèles distincts, deux lignes, deux IDs. On ne fusionne jamais un unknown avec un connu.
- **IDs déterministes.** `uuid5(NAMESPACE, "model|" + join(tuple d'identification, "|"))`.
  Re-run → mêmes IDs. Corriger un alias change l'ID : c'est voulu, l'ID suit l'identité, pas l'historique.
- **`variant`** :
  - `thinking` = thinking activé, effort et budget inconnus ;
  - `unknown-effort` = la source dit explicitement « effort setting unknown » (suffixe `_unknown` chez Epoch) ;
  - vide si `reasoning_level` ou `reasoning_tokens` est connu — le thinking est alors implicite
    (les noms machine `_high` d'Epoch n'ont pas de variant).
- **`score ∈ [0, 1]`** (pas de pourcentages).
- **Dédup**, dans cet ordre : doublons exacts fusionnés ; sinon Kaggle gagne (`kaggle_wins`) ;
  sinon `max`.

## Conventions de nommage, par source

Résultat d'un audit exhaustif du snapshot 2026-08-19, rejoué sur le snapshot courant
(2026-08-28) : les noms non résolus remontent dans les rapports du notebook.

| Source | Champ | Format | Stratégie |
|---|---|---|---|
| `epoch` (ZIP) | `Model version` | nom machine `[fournisseur/]base[-date][_suffixe]` | découpe + `aliases.csv` pour les exceptions (32) |
| `epoch_live` | `model` | idem, 100 % propre | découpe seule (`aliases.csv` vide) |
| `kaggle` | `modelVersionSlug` | nom machine pur, `-default` à retirer, jamais d'effort | découpe seule (`aliases.csv` vide) |
| `rand` | `Model` | noms display libres (`Amazon Nova 1.0 Lite`) | énumération totale dans `aliases.csv` (41) |
| `seal` | `model` (JSON dans le HTML) | 5 encodages incompatibles | énumération totale dans `aliases.csv` (258) |

Les 5 encodages SEAL, pour mémoire : `Claude Opus 4 (Thinking)`, `Claude 3.5 Sonnet (June 2024)`,
`Claude-4-Opus-20250514-thinking`, `Deepseek-R1-0528`, `claude-opus-4-5-20251101-thinking`.
Aucune découpe ne les couvre tous — d'où l'énumération.

### Grammaire du nom machine (`helpers.split_name`)

« Nom machine » = nom au format machine, ex. `claude-opus-4-8_high` — la forme est fixe,
donc on la découpe en colonnes sans dictionnaire.

`[provider/]base[-date][_suffixe]`

- `_` introduit un **bouton de config**, `-` fait partie de **l'identité**
  (`kimi-k2-thinking` est un nom, pas un bouton).
- Vocabulaire des suffixes (case-insensitive), sur le dernier `_` seulement :

  | suffixe | effet |
  |---|---|
  | `minimal` `low` `medium` `high` `xhigh` `max` `none` | `reasoning_level` |
  | `<N>K` (ex. `24K`) | `reasoning_tokens = N × 1000` |
  | `thinking` | `variant = thinking` |
  | `unknown` | `variant = unknown-effort` |
  | hors vocabulaire | le `_` fait partie du nom, rien n'est découpé |

- **Date** extraite uniquement en fin de base, aux formats `-YYYY-MM-DD` ou `-YYYYMMDD` → `snapshot`.
  Sous-extraction **délibérée** : `2507`, `0528`, `03-2025` restent dans `base_model`. Trop ambigus.
- Le préfixe `provider/` (un seul `/`) est retiré.

## Les trois gestes

### Corriger un nom mal traduit

1. Dans `database/scores.csv`, trouver la ligne fautive → colonne `feed` = la source.
2. Éditer `input/feed/<feed>/aliases.csv`. Colonnes :
   `raw_name,base_model,reasoning_level,reasoning_tokens,snapshot,variant,note`.
   `raw_name` = la chaîne brute exacte (après strip des `*`/`†` et blancs de fin).
3. `base_model` vide = **DROP délibéré** (ex. `Unsafety Llama` dans `rand`). Mettre la raison dans `note`.
4. Run All. L'alias gagne toujours sur la découpe — à une nuance près chez Epoch : un effort lu
   dans le champ affiché `Name` peut compléter une identité que l'alias a laissée vide.

### Ajouter une source (ex. MazeBench)

1. `input/feed/mazebench/` : les données brutes + un `aliases.csv` (même vide, mais avec l'en-tête).
2. Une entrée dans le dict `SOURCES` (cellule Setup) : nom du feed → stratégie (`découpe` ou `énumération`).
3. Une cellule dictionnaire (son `_SPEC` : ce qu'on ingère ; son `_SKIP` : ce qu'on écarte, avec la
   raison) et une cellule `translate_<source>` qui rend les sextuplets.
4. Une entrée dans le dict `TRANSLATE` de la cellule « La boucle » (un assert le rappelle sinon).
5. Run All.

**Règle `_SPEC`/`_SKIP`** — noms réels : `FILE_SPEC`/`FILE_SKIP` (epoch), `LIVE_TASK_SPEC`/`LIVE_TASK_SKIP`
(epoch_live), `KAGGLE_SPEC` (kaggle), `SEAL_SPEC`/`SEAL_SKIP` (seal) ; `rand` n'en a pas besoin, ses
benchmarks sont ses colonnes. Toute entrée qui n'est ni dans l'un ni dans l'autre est **signalée**.
Jamais ingérée en silence, jamais droppée en silence. Un feed qui change de forme se voit.

### Ajouter une colonne metadata

1. Un fichier dans `input/metadata/`. Clé de jointure :
   `base_model` pour les modèles (cf. `organizations.csv`), le nom du benchmark pour les benchmarks
   (colonne `benchmark` dans `categories.csv` et `floors.csv`).
2. Une cellule dans la passe 2 (avec son petit titre markdown `### 3x — ...`, comme les voisines) qui
   joint le fichier **et imprime ses restes** (clés du fichier qui ne matchent aucune ligne, lignes sans
   metadata). Copier une cellule voisine (`categories.csv`) : réassigner le dataframe depuis le merge et
   finir par `.fillna({"nouvelle_colonne": ""})`, sinon des `NaN` partent dans le CSV.
3. Ajouter la nouvelle colonne à `MODEL_COLS` ou `BENCH_COLS` dans la cellule Setup — sans ça elle est
   silencieusement absente du CSV écrit.
4. Run All. Aucun ID ne bouge. Le test de régression signale l'écart (colonne nouvelle) : c'est voulu,
   re-bénir avec `cp database/*.csv tests/expected_database/` puis re-run.

## Lancer

```bash
pip install -r requirements.txt
python3 refresh.py          # obligatoire au premier run : récupère les pages SEAL
jupyter lab pipeline.ipynb
```

Le notebook n'a besoin que de `pandas` ; `refresh.py` n'utilise que la stdlib. Vérifiez
juste que le `python3` de votre PATH est bien celui de l'environnement où pandas est
installé — le `python3` d'une base conda ne l'a en général pas.

Restart Kernel → **Run All**, de haut en bas. Les checks de la dernière section doivent passer.
Deux runs successifs doivent produire un `database/` **bit à bit identique** — c'est le test de
déterminisme, si ça diverge il y a un `dict`/`set` non trié quelque part.

La dernière cellule compare `database/` à la copie bénie `tests/expected_database/` (test de
régression). Un écart voulu — nouveau feed, alias corrigé — se re-bénit avec :
`cp database/*.csv tests/expected_database/`.

### Rafraîchir les feeds

`python3 refresh.py` (stdlib seule, hors notebook) réécrit `input/feed/`, puis Run All.
RAND reste figé (rapport Dev et al. 2025). Les nouveautés ne sont jamais ingérées en douce :
fichiers / tâches / boards inconnus et noms non résolus remontent dans les rapports du notebook,
à curer ensuite dans les `*_SPEC` et les `aliases.csv`. Provenance (URL, date, sha256) :
`input/feed/provenance.json`.

## Licence et sources

Le code, le notebook, les dictionnaires curés et les trois CSV de `database/` sont sous
**CC-BY-4.0** (`LICENSE`).

Les scores en amont ont leurs propres conditions — Epoch AI en CC-BY, Kaggle sous ses CGU,
RAND sous citation RR-A3797-1, Scale SEAL sans licence ouverte. Détail par feed, et ce qu'il
faut créditer en republiant : [`NOTICE.md`](NOTICE.md).

**Dépôt lié.** [`ECI_Bayesian`](https://github.com/General-Purpose-AI-Policy-Lab/ECI_Bayesian)
recrée l'Epoch Capabilities Index sur les mêmes feeds. Il ne consomme pas `database/` :
il tourne sur son propre notebook de pipeline, dans un schéma différent.
