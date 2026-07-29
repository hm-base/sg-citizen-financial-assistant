# Data layout

| Location | What | Where stored |
|---|---|---|
| `data/raw/{text,video,images}/` | Large source files (HTML/PDF/MP4) | **Google Drive** (not GitHub) |
| `data/meta/` | JSON sidecars per `doc_id` | GitHub |
| `data/sources_*.yaml` | Catalogs | GitHub |
| `data/faiss/` | Built index | Local / Drive (gitignored) |

Shared Drive folder: https://drive.google.com/drive/folders/1VBU3zGuh9pyByyOETJ6NUDP-3kDBgaZu

After cloning the repo, download Drive `text/`, `video/`, `images/` into `data/raw/` so paths match the yaml `local_path` entries. Runtime does **not** call Drive or GitHub — everything runs from local disk.
