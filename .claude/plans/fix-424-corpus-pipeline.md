# Implementation plan — #424

1. Expose the missing corpus stages over HTTP: `:segment`, `:index`, `:publish`.
2. Segmentation publishes a body passage so indexing has searchable text; `citable` means a
   publishable passage exists.
3. Make `POST /corpus/ingestion-runs` process `paths` and record attempted/accepted/quarantined/failed.
4. Add `CORPUS_MAX_PAGES` and `DOCUMENT_TOO_LARGE` before extraction starts.
5. Prove the API-only document → segment → index → snapshot → pack sequence.
