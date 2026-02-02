ECM Polarimetry Documentation
=============================

**Ellipsometric Calibration Method for Mueller Matrix Polarimetry**

ECM Polarimetry is a Python package for calibrating and analyzing spectroscopic
Mueller matrix polarimeters with dual rotating compensators.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   theory
   configuration

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/index

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index

Features
--------

- Complete ECM calibration pipeline for transmission mode
- Lu-Chipman polar decomposition of Mueller matrices
- Publication-quality visualization tools
- Command-line interface for batch processing
- Comprehensive test suite (383 tests)

Quick Example
-------------

.. code-block:: python

   from ecm.config import ECMConfig
   from ecm.core import calibrate_transmission
   from ecm.postprocessing import lu_chipman_decomposition

   # Run calibration
   cfg = ECMConfig()
   result, diagnostics = calibrate_transmission(cfg)

   # Decompose Mueller matrix
   lu_result = lu_chipman_decomposition(M_normalized)
   print(f"Retardance: {lu_result.R_deg.mean():.1f} degrees")

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
