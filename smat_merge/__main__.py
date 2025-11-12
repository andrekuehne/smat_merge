from smat_merge.gui import SMatMergeApp
import os
import sys

def main():
    # Add the project root to the Python path to allow absolute imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    app = SMatMergeApp()
    app.mainloop()

if __name__ == "__main__":
    main()
