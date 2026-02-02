"""
ECM Calibration Test Suite

This package contains pytest tests for validating the ECM calibration implementation.

Test Modules
------------
test_mueller_matrices
    Tests for Mueller matrix generators (rotation, polarizer, retarder, identity)
test_io
    Tests for data loading functions
test_config
    Tests for configuration dataclasses

Running Tests
-------------
From the project root directory:

    pytest tests/ -v

With coverage:

    pytest tests/ --cov=ecm --cov-report=html

Test Categories
---------------
The tests validate:
1. Mathematical correctness of Mueller matrix formulas
2. Physics convention compliance (Compain 1999)
3. Data loading from binary files
4. Configuration validation and serialization
"""
