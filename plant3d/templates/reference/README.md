# Reference templates (empty on purpose)

Place here the real Excel file exported by Plant 3D's Catalog Builder for
`HDPE_SEGMENTED_ELBOW`:

```
Catalog Builder -> Create Catalog Template -> Elbow
  -> Custom Parametric Shape -> HDPE_SEGMENTED_ELBOW -> Export to Excel
```

Until a `.xls`/`.xlsx` file exists in this directory,
`plant3d/catalog/catalog_builder_excel_exporter.py` always raises
`ReferenceTemplateRequiredError` — the exact column layout Catalog
Builder expects is not guessed anywhere in this codebase. See
`docs/PLANT3D_CATALOG_WORKFLOW.md`.
