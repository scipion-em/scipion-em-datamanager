====================
Scipion Data Manager
====================

This project is a Scipion plugin to make depositions or retrieve data to/from several data portals:

- CryoEM Workflow Viewer: http://nolan.cnb.csic.es/cryoemworkflowviewer
- Onedata (using the https://cryo-em-docs.readthedocs.io/en/latest/user/download_all.html script developed by Masaryk University)

=====
Setup
=====

You will need to use `Scipion3 <https://scipion-em.github.io/docs/docs/scipion
-modes/how-to-install.html>`_ to run these protocols.

1. **Install the plugin:**

- **Install the stable version (Not available yet)**

    Through the **plugin manager GUI** by launching Scipion and following **Configuration** >> **Plugins** or

.. code-block::

    scipion installp -p scipion-em-datamanager


- **Developer's version**

    1. Download repository:

    .. code-block::

        git clone https://github.com/scipion-em/scipion-em-datamanager.git

    2. Install:

    .. code-block::

        scipion3 installp -p path_to_scipion-em-datamanager --devel

2.  Extra steps:

- If you want to make depositions to http://nolan.cnb.csic.es/cryoemworkflowviewer, you must register there first and obtain an API token.

