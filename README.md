# flarepred
Repository for the early-onset flare trigger system that will be utilized in the FOXSI and HI-C lauches.

## To Set-up

### 1. Download the repository

Either 

* Download the `flarepred` repository manually (`<> Code`>>`Download ZIP`) and place in a directory of your choice; or
*  navigate to that directory on your machine in the command line and use `git clone https://github.com/pet00184/flarepred.git`. 
  
You now have the `flarepred` package.

### 2. Python virtual environment

To avoid polluting your base python environemnt let's create a virtual Python environment to work in. 

1. **Conda** <sub><sup>[recommended]</sup></sub>

	We can create the environment with [Conda/Miniconda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) where we can just type `conda create -n flarepred-env python=3.11.3 pip` in the command line.

	* Now we can activate the environment with `conda activate flarepred-env`; and
	* deactivate with `conda deactivate`.

	(See [here](https://docs.conda.io/en/latest/miniconda.html) for information on installing miniconda.)

2. **PIP**

	Another way is just to use PIP directly to create the virtual environment; however, more set-up is needed.

	First, ensure Python 3.11 is installed on your machine. A way to do this is with [Homebrew](https://formulae.brew.sh/formula/python@3.11) via 
	
	* `brew install python@3.11`
	
	It should then be possible to create a virtual environment with with this specific version of Python using
	
	* `python3.11 -m venv flarepred-env`

	After this, in the Mac/Unix terminal, the environment 
	
	* can be activated with `source env/bin/activate` or, if the correct paths aren't set-up, `source .../env/bin/activate`; and
	* can be deactivated with `deactivate`.

	where `...` here represents the location of the virtual environment. (See [here](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) for more information on working with Python environments set-up this way.) 
	
	You may need to find where the virtual environment is saved. I had to search for the environment but depending how paths are set-up it may be obvious. In this example, the environment will be in a folder called `flarepred-env` somewhere.
	

### 3. Installing `flarepred` requirements

Make sure you are in the `flarepred` directory and have the activated the virtual environment, type `pip install -r requirements.txt`. This install all the required packages used in `flarepred`.

Now, as long as you are in your virtual environment, you can use the methods in `flarepred` without issue while in any directory 

### 4. Example
	
1. To run the main GUI, now named ELSA, run the following:
 
	* `python3 .../flarepred/RealTime/ELSA_window.py`
	
	This window is the main window we will be using for the flare campaign, which includes actionable plots that directly relate to the trigger.

2. To run ELSA's complimentary GUI (named ANNA), run the following:

 	* `python3 .../flarepred/RealTime/ANNA_window.py`

 	This window includes complimentary plots that are not essential to the trigger, such as EOVSA data, EVE 30nm data, and running differences of XRSB and EVE.

See the [RealTime module](https://github.com/pet00184/flarepred/tree/main/RealTime) for a more detailed description on ELSA and ANNA.

### 4. At the end

Remember to deactivate the Python virtual environment or just close the terminal being worked in. 

## Updating

If your local code needs updated because of a change on Github then `git pull` (or `git pull origin main`) should work.

If local changes have been made to the code that are not tracked or consistent with the newer version on Guthub then perform the following:

* _If you require the local changes to be saved somewhere before resetting_, make sure to do the following, otherwise proceed to reset your local branch
  * `git commit -a -m "local branch work"` 
  * `git branch local-work` 

* To force your local coode to be what is on Github then
  * `git fetch origin`
  * `git reset --hard origin/main`.

## CHANGES FROM TRIAL RUN

**There is no longer a hold option that incurs a 30-minute deadtime in the gui** This option was meant for trial runs, but we don't want the GUI out of comission if we decide to hold in the actual campaign. Now, there is a "Not Launching" button that may be pressed, that moves ELSA back into searching state. If the trigger condition is met again, you will need to continuously press this button (or just wait until you reach the gradual phase of whatever flare you are choosing to ignore.)

