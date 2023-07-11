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

1. While in *any* directory with the virtual environment activated, you can run 

	* `python3 .../flarepred/RealTime/run_realtime_algorithm.py`,

	where `...` is the location of the `flarepred` directory. 

	This will run the `run_realtime_algorithm.py` script and save the output 	products at `$PATH$/flarepred/RealTime/SessionSummaries/EXAMPLE_HISTORICAL_RUN2/` (the number after `EXAMPLE_HISTORICAL_RUN` may vary).
	
2. Run the following
 
	* `python3 .../flarepred/RealTime/main_window.py`
	
	to use GUI under developement which has buttons to stop/start the GOES data plotting and a time display of REALTIME data. Output products are handled the same as in *Example 1*.
	
3. Run the following
 
	* `python3 .../flarepred/RealTime/main_window.py historical`
	
	to view the GUI using historical data. This can be used to gain familiarity or for testing, etc.

See the [RealTime module](https://github.com/pet00184/flarepred/tree/main/RealTime) for a more detailed description on the workings of the package.

### 4. At the end

Remember to deactivate the Python virtual environment or just close the terminal being worked in. 

## Caveats

At the minute

* The `main_window.py` GUI will **only** allow a launch when the automated trigger condition has been met (the status will change to "triggered" and the LED will flash yellow). 

* If launched, the GUI must be run until the flare has stopped for the post-flare analysis process to be complteted succesfully.