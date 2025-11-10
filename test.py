import psutil
import os
cmdline = psutil.Process().cmdline()
print(os.getcwd(),cmdline)
