# Data layout

| Location | What | Where stored |
|---|---|---|
| `datasets/<topic>/markdown/*.md` | **Canonical sources** (YAML frontmatter + body) per `metadata_format.md` / team guide | **GitHub** (text) |
| `datasets/<topic>/video/*.mp4` | Non-core videos | **Google Drive** |
| `datasets/<topic>/pdf/*.pdf` | Original PDFs (CCP factsheets) | **Google Drive** (optional; text already in `.md`) |
| `data/raw/{text,video,images}/` | Local runtime mirror for the indexer | Local / Drive sync |
| `data/metadata/` | JSON sidecars | GitHub |
| `data/metadata/sources_*.yaml` | Catalogs | GitHub |

Shared Drive: https://drive.google.com/drive/folders/1VBU3zGuh9pyByyOETJ6NUDP-3kDBgaZu

Drive folder mapping for upload:

```
Drive text/<topic>/*.md   ← datasets/<topic>/markdown/
Drive video/<topic>/*.mp4 ← datasets/<topic>/video/
Drive images/             ← (empty / future infographics)
```

GitHub and Drive do **not** need to talk to each other. Clone + download onto one machine, then run.
