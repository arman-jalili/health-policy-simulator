# Plan — #434

1. Enrich `DocumentNotCitable` with measured quality/threshold/pages/characters; use one message from both
   `SegmentArticleHandler` and `IndexIngestedPassagesHandler`.
2. Catch `DocumentNotCitable` in `StartIngestionRunHandler` and record `QUARANTINED` with that code+reason;
   keep `FAILED` for `OcrUnavailable`, IO and other operational errors.
3. Rely on the existing content-hash path: a document with no extraction is re-extracted; a low-quality one
   reports the same quarantine again.
4. Test accepted / quarantined / failed side by side, quarantine re-runs, and single `:index` vs batch reason
   agreement.
