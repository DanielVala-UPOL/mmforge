# Changelog

All notable changes to MMForge will be documented in this file.

---

## [v1.2] - 2026-02-09

### Added
- **Tutorial Data mode**: Bundled example calibration and sample data for learning the workflow
- New "Tutorial Data" option in Calibration Mode selector

### Changed
- Data Paths inputs disabled in Tutorial mode (auto-configured)
- Save/Load/Export buttons disabled in Tutorial mode
- Session state keys: `tutorial_mode`, `saving_disabled`

### Notes
- Tutorial data includes: calibration files + HWP and QWP samples
- Perfect for first-time users to explore without real measurements

---

## [v1.1] - 2026-02-09

### Added
- **Auto-detect rotator steps**: Rotator steps (n_positions) are now automatically detected from calibration file dimensions during file discovery
- **Calibration Mode selector**: New mode selector (Transmission/Reflection/Combined) replaces manual "Acquisition Settings" input
- **Changelog expander**: About page now includes version history

### Changed
- Removed manual "Angular Positions" input from Configuration page
- File discovery now validates dimension consistency across all calibration files

### Notes
- Reflection and Combined modes are placeholders for future releases
- ECM calibration algorithm unchanged

---

## [v1.0] - 2026-02-01

### Initial Release
- ECM calibration for Mueller matrix spectroscopic polarimetry
- Transmission mode support
- Lu-Chipman polar decomposition
- Interactive Plotly visualizations
- Save/load calibration results
