ECM Theory
==========

This section provides an overview of the Eigenvalue Calibration Method (ECM)
and the Lu-Chipman polar decomposition.

Mueller Matrix Polarimetry
--------------------------

A Mueller matrix polarimeter measures the complete polarimetric response of a
sample by determining its 4x4 Mueller matrix **M**. The Mueller matrix relates
the input and output Stokes vectors:

.. math::

   \mathbf{S}_{out} = \mathbf{M} \cdot \mathbf{S}_{in}

ECM Measurement Model
---------------------

The ECM uses a dual rotating compensator (DRC) configuration with the following
optical arrangement:

::

   Light Source → PSG → Sample → PSA → Detector

Where:
- **PSG**: Polarization State Generator (polarizer + rotating retarder)
- **PSA**: Polarization State Analyzer (rotating retarder + polarizer)

The measured intensity as a function of the rotation angles can be expressed as:

.. math::

   I(\omega_1, \omega_2) = \mathbf{a}^T \cdot \mathbf{M} \cdot \mathbf{w}

where **a** and **w** are the analyzer and generator Stokes vectors.

After Fourier decomposition, the measured intensity matrix **B** relates to the
sample Mueller matrix through:

.. math::

   \mathbf{B} = \mathbf{A} \cdot \mathbf{M} \cdot \mathbf{W}

where **A** and **W** are the 4x4 instrument matrices.

Eigenvalue Calibration
----------------------

The ECM calibration procedure uses calibration samples with known Mueller matrices
(air, polarizers, retarders) to determine **W** and **A**.

Building the K Matrix
~~~~~~~~~~~~~~~~~~~~~

For each calibration sample *i*, we construct an H matrix:

.. math::

   \mathbf{H}_i = (\mathbf{M}_i \otimes \mathbf{I}_4) \cdot \mathbf{C}

where **C** is derived from the relationship:

.. math::

   vec(\mathbf{B}) = (\mathbf{W}^T \otimes \mathbf{A}) \cdot vec(\mathbf{M})

The K matrix accumulates information from all calibration samples:

.. math::

   \mathbf{K} = \sum_i \mathbf{H}_i^T \mathbf{H}_i

Solving for W
~~~~~~~~~~~~~

The instrument matrix **W** (in vectorized form) is the eigenvector corresponding
to the smallest eigenvalue of **K**:

.. math::

   \mathbf{K} \cdot vec(\mathbf{W}) = \lambda_{min} \cdot vec(\mathbf{W})

For a well-conditioned calibration, the ratio of the smallest to second-smallest
eigenvalue should be small (< 10^-6).

Calculating A
~~~~~~~~~~~~~

Once **W** is determined, **A** is calculated from the air measurement:

.. math::

   \mathbf{A} = \mathbf{B}_{air} \cdot \mathbf{W}^{-1}

Lu-Chipman Decomposition
------------------------

The Lu-Chipman polar decomposition factorizes any Mueller matrix into a product
of three physically meaningful components:

.. math::

   \mathbf{M} = \mathbf{M}_\Delta \cdot \mathbf{M}_R \cdot \mathbf{M}_D

where:

- :math:`\mathbf{M}_D`: Diattenuator (dichroism)
- :math:`\mathbf{M}_R`: Retarder (birefringence)
- :math:`\mathbf{M}_\Delta`: Depolarizer

Extracted Parameters
~~~~~~~~~~~~~~~~~~~~

**Diattenuation (D)**

.. math::

   D = \sqrt{m_{01}^2 + m_{02}^2 + m_{03}^2} / m_{00}

Range: [0, 1] where 0 = no diattenuation, 1 = perfect polarizer

**Retardance (R)**

.. math::

   R = \arccos\left(\frac{tr(\mathbf{m}_R) - 1}{2}\right)

Range: [0, π] radians

**Depolarization Index (DI)**

.. math::

   DI = \frac{\sqrt{\sum_{i,j} m_{ij}^2} - m_{00}^2}{3 \cdot m_{00}^2}

Range: [0, 1] where 1 = non-depolarizing, 0 = ideal depolarizer

**Fast Axis Orientation**

The orientation of the fast axis is given by angles ψ (azimuth) and χ (ellipticity):

.. math::

   \psi = \frac{1}{2} \arctan\left(\frac{r_2}{r_1}\right)

.. math::

   \chi = \frac{1}{2} \arcsin(r_3 / R)

where (r_1, r_2, r_3) is the retardance vector.

References
----------

1. Compain, E., Poirier, S., & Drevillon, B. (1999). General and self-consistent
   method for the calibration of polarization modulators, polarimeters, and
   Mueller-matrix ellipsometers. *Applied Optics*, 38(16), 3490-3502.

2. Lu, S. Y., & Chipman, R. A. (1996). Interpretation of Mueller matrices based
   on polar decomposition. *Journal of the Optical Society of America A*, 13(5),
   1106-1113.

3. Goldstein, D. H. (2011). *Polarized Light* (3rd ed.). CRC Press.
