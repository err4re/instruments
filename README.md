# instruments

Lab instrument drivers in Python


## Installation

- to install the package in *develop mode*, run from the upper directory in Anaconda prompt (in the chosen environment, i.e. 'base'):

`pip install -e instruments`

- to import a module in python console/script (example with yoko750 driver):

`from instruments import yoko750`

- then use as:

`y = yoko750.Yoko750(...)`


### Note

The *pip develop mode* (`-e`) allows modifications of the source code to take effect without reinstalling. Reloading may be necessary after a modification of the source code (TO CHECK). Or use the following ipython magics before importing:

`%load_ext autoreload`

`%autoreload 2`

