# ECM Polarimetry GUI - Phase 6 Entry Prompt

## Context
Phases 0-5 are complete. The app has full functionality: calibration, sample processing, Lu-Chipman decomposition, and visualization. Phase 6 focuses on polish and enhancements.

## Your Task
Implement the Phase 6 improvements described in `PHASE6_INSTRUCTIONS.md`.

## Instructions
1. Read `PHASE6_INSTRUCTIONS.md` completely before starting
2. Follow the implementation order:
   - Priority 1: PNG export, Reset Session, Caching
   - Priority 2: Error messages, Batch export, Persist selections
   - Priority 3: Validation warnings, UI improvements (if time permits)
3. Test after each change: `streamlit run streamlit_app/app.py`

## Key Files
- `streamlit_app/utils/export.py` - Has `export_figure_png()` ready to use
- `streamlit_app/pages/3_Processing.py` - Needs PNG export buttons enabled
- `streamlit_app/pages/4_Parameters.py` - Needs PNG export buttons enabled
- `streamlit_app/app.py` - Add Reset Session button
- `streamlit_app/components/plots_plotly.py` - Add caching decorators

## Rules
- DO NOT modify physics/math logic in `ecm/` package
- Keep code simple and well-commented
- Test each feature after implementing
- Report progress after completing each priority level

## Start
Please read `PHASE6_INSTRUCTIONS.md` now and begin with Priority 1 tasks.
