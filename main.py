"""Main program: Convert PDF to PNG images, then process each image with the screenshot tool"""

import dis
import os
import time
import threading
import cv2
import shutil
import glob
import argparse
from notebooklm2ppt.cli import main

if __name__ == "__main__":
    main()
