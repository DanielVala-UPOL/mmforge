# ECM Polarimetry GUI - Phase 2 Entry Prompt

## Context
Phase 0 (debugging) and Phase 1 (basic layout) are complete. The app runs and has basic structure. Now we refine the UI/UX.

## Your Task
Implement the UI/UX refinements described in `UI_UX_PHASE2_INSTRUCTIONS.md`.

## Instructions
1. Read `UI_UX_PHASE2_INSTRUCTIONS.md` completely before starting
2. Follow the step-by-step instructions in that document
3. Implement changes in this order:
   - Install required packages (`streamlit-file-browser`, `streamlit-antd-components`)
   - Global changes (remove icons, implement sticky header)
   - Page-specific changes (Home → Config → Calibration → Processing → Parameters)
   - Update `file_browser.py` component
4. Use the verification checklist at the end to confirm all changes

## Rules
- DO NOT modify physics/math logic in the `ecm/` package
- Test after each major change: `streamlit run streamlit_app/app.py`
- Report progress after completing each page
- Ask if anything is unclear

## Start
Please read `UI_UX_PHASE2_INSTRUCTIONS.md` now and begin implementation.
