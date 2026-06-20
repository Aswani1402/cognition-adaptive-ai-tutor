# Notebook Save Frontend Fix Report

Added `saveNotebookNote` in `src/lib/api.ts` and wired Notebook page save actions to the backend route instead of localStorage.

The button now displays saved state and reports failure text when the backend returns a warning.
