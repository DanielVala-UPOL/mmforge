Installation
============

Requirements
------------

ECM Polarimetry requires Python 3.9 or later.

Dependencies
~~~~~~~~~~~~

The following packages are required and will be installed automatically:

- numpy >= 1.24.0
- scipy >= 1.10.0
- matplotlib >= 3.7.0
- pyyaml >= 6.0
- tqdm >= 4.65.0
- lmfit >= 1.2.0

Installation from Source
------------------------

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/yourusername/ecm-polarimetry.git
   cd ecm-polarimetry
   pip install -e .

Development Installation
------------------------

To install with development dependencies (pytest, black, mypy, etc.):

.. code-block:: bash

   pip install -e ".[dev]"

Documentation Installation
--------------------------

To build the documentation locally:

.. code-block:: bash

   pip install -e ".[docs]"
   cd docs
   make html

The documentation will be available at ``docs/_build/html/index.html``.

Verifying Installation
----------------------

After installation, verify that everything is working:

.. code-block:: bash

   # Check version
   python -c "import ecm; print(ecm.__version__)"

   # Run tests
   pytest tests/ -v

   # Check CLI
   ecm-calibrate --help

Troubleshooting
---------------

ImportError: No module named 'ecm'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure you installed the package with ``pip install -e .`` from the
project root directory.

Tests failing
~~~~~~~~~~~~~

If tests are failing, ensure you have the latest dependencies:

.. code-block:: bash

   pip install -e ".[dev]" --upgrade
