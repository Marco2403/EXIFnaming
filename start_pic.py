#!/usr/bin/env python3
exec (open("./start.py").read())

print(os.getcwd())
os.chdir("E:\\Bilder\\bearbeitung\\tags")
print(os.getcwd())

import tags
