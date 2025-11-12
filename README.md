# smat-merge

A tool to reconstruct a full N-port S-matrix from multiple smaller S-parameter measurements performed on subsets of the total ports. This is useful when characterizing an N-port device with a VNA that has fewer than N ports.

The tool averages the contributions for each S-parameter where measurements overlap, providing a composite S-matrix for the full device.

Note: This was mostly coded using Github Copilot, but verified to work on real test datasets. Also, the functional and CLI approaches are covered by tests.

## Features

-   **User-friendly Graphical User Interface (GUI)** for interactive merging.
-   **Command-Line Interface (CLI)** for scripting and automation.
-   **Core Python function** for direct integration into `scikit-rf` workflows.
-   Built on the powerful `scikit-rf` and `numpy` libraries.

## Installation

This project uses `uv` for fast environment and package management.

1.  **Install `uv`**

    Before you begin, you need to have `uv` installed on your system. You can find the official installation instructions here: [**astral-sh/uv**](https://docs.astral.sh/uv/getting-started/installation/).

2.  **Set up the Environment and Install Dependencies**

    Once `uv` is installed, you can either set up the environment manually or use the provided start scripts, which will handle it for you.

    **Method 1: Automatic Setup (Recommended)**

    Simply run one of the start scripts. They will automatically create a virtual environment and install all necessary dependencies if they are not already present.
    -   On Windows PowerShell: `.\start.ps1`
    -   On Windows Command Prompt: `.\start.bat`

    **Method 2: Manual Setup**

    If you prefer to set up the environment manually, open a terminal in the project root directory and run the following commands:

    ```bash
    # Create a virtual environment in a .venv folder
    uv venv

    # Install/sync the dependencies from pyproject.toml
    uv pip install -e .
    ```

## Usage

`smat-merge` can be used in three ways: as a standalone GUI, as a command-line script, or as a Python function.

### 1. Graphical User Interface (GUI)

The easiest way to use the tool is via the GUI. If you have already set up the environment, you can launch the application with the convenience scripts.

-   On Windows PowerShell:
    ```powershell
    .\start.ps1
    ```
-   On Windows Command Prompt:
    ```batch
    .\start.bat
    ```

This will launch a window where you can:
1.  Set the total number of ports for the final device.
2.  Add your partial Touchstone files (`.s4p`, `.s2p`, etc.).
3.  For each file, map the VNA ports to the corresponding Device Under Test (DUT) ports.
4.  Specify an output file and merge the measurements.

<img width="600"  alt="S-Parameter Merge GUI" src="https://github.com/user-attachments/assets/88a489ad-b9af-432f-822d-d4351ed8de68" />

### 2. Command-Line Interface (CLI)

For automation and scripting, you can use the `reconstruct_nport.py` script directly.

The syntax requires specifying the total number of ports and a list of measurement configurations, where each configuration is a string combining the file path and its port mapping.

**Syntax:**
`python -m smat_merge.reconstruct_nport --n-ports <N> <file1.sNp>:<p1,p2,...> <file2.sNp>:<q1,q2,...>`

**Example:**
Imagine you have a 5-port device and have measured it with a 4-port VNA, resulting in four `.s4p` files. The command to reconstruct the full `.s5p` file would be:

```bash
python -m smat_merge.reconstruct_nport --n-ports 5 ^
  data/COIL_3-50OHM.S4P:1,2,3,4 ^
  data/COIL_4-50OHM.S4P:1,2,3,5 ^
  data/COIL_5-50OHM.S4P:1,2,4,5 ^
  data/reconstructed_5port.s5p:1,3,4,5
```
The reconstructed network will be saved as `reconstructed_5port.s5p` in the current directory.

### 3. Python Function

For maximum flexibility, you can import the `reconstruct_nport` function directly into your Python scripts.

**Example:**

```python
import skrf as rf
from smat_merge.reconstruct_nport import reconstruct_nport

# 1. Load your partial network measurements
net1 = rf.Network('data/COIL_3-50OHM.S4P') # Measured on ports 1,2,3,4
net2 = rf.Network('data/COIL_4-50OHM.S4P') # Measured on ports 1,2,3,5
# ... load all other networks

networks = [net1, net2] # Add all networks to a list

# 2. Define the DUT port mapping for each measurement
#    (1-based port numbers)
port_sets = [
    (1, 2, 3, 4),
    (1, 2, 3, 5),
    # ... add mappings for all other networks
]

# 3. Reconstruct the full network
#    Specify the total number of DUT ports (e.g., 5)
full_net, counts = reconstruct_nport(
    networks=networks,
    port_sets=port_sets,
    n_ports=5
)

# 4. Save the result
full_net.write_touchstone('my_reconstructed_device')

print("Reconstruction complete.")
print("Matrix of measurement counts for each S_ij:")
print(counts)
```

## How It Works

The script initializes an empty N x N S-matrix (where N is the total number of DUT ports). For each partial measurement file provided, it reads the S-parameters and adds them to the corresponding entries in the full N x N matrix based on the user-defined port mapping.

A separate counter matrix keeps track of how many measurements contributed to each `S_ij` element.

Finally, each element in the summed S-matrix is divided by its corresponding count to get an average value. If an `S_ij` element was never measured, its value remains zero.
