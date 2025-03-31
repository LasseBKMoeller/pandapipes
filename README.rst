During an internship at GELSENWASSER Energienetze GmbH (https://www.gw-energienetze.de) I extended pandapipes with the functionality to calculate the amount of water one can get from a hydrant in case of fire.

For this a new component called hydrant has been created that can be added to the grid in two ways: Either at a junction or on a pipe (for now those ways cannot be mixed). For a grid with sources, sinks, ext_grids etc. and hydrants a hydrant calculation can be done which finds for all hydrants the maximal amount of water which can be obtained at the hydrants, such that the minimal pressure in the grid does not fall below a certain threshold.

Tutorials on how to use the new functions can be found in the tutorials folder (in german).

If you have any questions you can ask me or Philipp Jünemann at Gelsenwasser Energienetze:
philipp.juenemann@gw-energienetze.de



.. image:: ./doc/source/pics/pp.svg
   :target: https://www.pandapipes.org
   :width: 300em
   :alt: logo

|

.. image:: https://badge.fury.io/py/pandapipes.svg
   :target: https://badge.fury.io/py/pandapipes
   :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/pandapipes.svg
   :target: https://pypi.python.org/pypi/pandapipes
   :alt: versions

.. image:: https://readthedocs.org/projects/pandapipes/badge/
   :target: http://pandapipes.readthedocs.io/
   :alt: docs

.. image:: https://codecov.io/gh/e2nIEE/pandapipes/branch/master/graph/badge.svg
   :target: https://codecov.io/github/e2nIEE/pandapipes?branch=master
   :alt: codecov

.. image:: https://api.codacy.com/project/badge/Grade/86c876ab23fc40d98e85f7d59bdef928
   :target: https://app.codacy.com/gh/e2nIEE/pandapipes/dashboard
   :alt: Codacy Badge

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :target: https://github.com/e2nIEE/pandapipes/blob/master/LICENSE
   :alt: BSD

.. image:: https://pepy.tech/badge/pandapipes
   :target: https://pepy.tech/project/pandapipes
   :alt: pepy

.. image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/e2nIEE/pandapipes/master?filepath=tutorials
   :alt: binder


A pipeflow calculation tool that complements `pandapower <https://www.pandapower.org>`_ in the
simulation of multi energy grids, in particular heat and gas networks. More information can be found on `www.pandapipes.org <https://www.pandapipes.org>`_.

Getting started:

- `Installation Notes <https://www.pandapipes.org/start/>`_
- `Documentation <https://pandapipes.readthedocs.io/en/latest/>`_
- `Tutorials on github <https://github.com/e2nIEE/pandapipes/tree/master/tutorials>`_
- `Interactive tutorials on Binder <https://mybinder.org/v2/gh/e2nIEE/pandapipes/master?filepath=tutorials>`_



pandapipes is a development of the Department for Distribution System Operation at the Fraunhofer
Institute for Energy Economics and Energy System Technology (IEE), Kassel, and the research group
Department for Sustainable Electrical Energy Systems (e2n), University of Kassel.


.. image:: ./doc/source/pics/iee.png
    :target: https://www.iee.fraunhofer.de/en.html
    :width: 350

|

.. image:: https://www.uni-kassel.de/uni/fileadmin/sys/resources/images/logo/logo-main.svg
    :target: https://www.uni-kassel.de/
    :width: 350

|

.. image:: ./doc/source/pics/e2n.png
    :target: https://www.uni-kassel.de/eecs/en/e2n/home
    :width: 250

|

We welcome contributions to pandapipes of any kind - if you want to contribute, please check out
the `pandapipes contribution guidelines <https://github.com/e2nIEE/pandapipes/blob/develop/CONTRIBUTING.rst>`_.
