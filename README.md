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

We can create the environment with [Conda/Miniconda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) where we can just type `conda create -n flarepred-env python=3.11.3 pip` in the command line [recommended]

* Now we can activate the environment with `conda activate flarepred-env`; and
* deactivate with `conda deactivate`.

(See [here](https://docs.conda.io/en/latest/miniconda.html) for information on installing miniconda.)

### 3. Installing `flarepred` requirements

Make sure you are in the `flarepred` directory and have the activated the virtual environment, type `pip install -r requirements.txt`. This install all the required packages used in `flarepred`.

Now, as long as you are in your virtual environment, you can use the methods in `flarepred` without issue while in any directory 

### 4. Example

While in *any* directory with the virtual environment activated, you can run 

* ` python3 $PATH$/flarepred/RealTime/run_realtime_algorithm.py`,

where `$PATH$` is the location of the `flarepred` directory. 

This will run the `run_realtime_algorithm.py` script and save the output products at `$PATH$/flarepred/RealTime/SessionSummaries/EXAMPLE_HISTORICAL_RUN2/` (the number after `EXAMPLE_HISTORICAL_RUN` may vary).

See the [RealTime module](https://github.com/pet00184/flarepred/tree/main/RealTime) for a more detailed description on the workings of the package.