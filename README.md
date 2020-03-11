# instruments

Lab instrument drivers in Python used at Collège de France


## Installation

- to install the package in *develop mode*, run from the upper directory in Anaconda prompt (in the chosen environment, i.e. 'base'):

`pip install -e instruments`

- to import a module in python console/script (example with yoko750 driver):

`from instruments import yoko750`

- then use as:

`y = yoko750.Yoko750(...)`


### Note

The *pip develop mode* (`-e`) allows modifications of the source code to take effect without reinstalling.

However, reloading is necessary after a modification of the source code. In python console (or a script), add the following after `from instruments import yoko750` :

`import importlib`

`importlib.reload(yoko750)`

Or use the following ipython magics before importing:

`%load_ext autoreload`

`%autoreload 2`

This will automatically reload any modified module.