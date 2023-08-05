macro_example = """
# Simple example showing how macros are supposed to work
import numpy as np
import matplotlib.pyplot as plt

# The pyafmsession object holds all the files and results computed by the software
print(dir(pyafmsession))

# Define function to plot a line
def foo():
    plt.plot(np.arange(0,20))
    plt.show()

# Run function
foo()
"""