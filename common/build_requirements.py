#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 19 08:49:26 2023

@author: david
"""

import os.path

filename = "./Pipfile"
libraries = []

if os.path.exists(filename):
    
    with open(filename) as file:
        lines = [line.rstrip() for line in file]
        
        for line in lines:
            if '"*"' in line:
                line = line.replace(' = "*"', '')
                libraries.append(line)
                
with open('requirements_clean.txt', 'w') as f:
    for line in libraries:
        f.write(f"{line}\n")