#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 13:25:03 2024

@author: jlwarner
"""

import os
os.chdir('/Users/jlwarner/Desktop/chip_seq/logs')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Gives number of lines in log file
with open(r"experimental_counts.log", 'r') as fp:
    lala = len(fp.readlines())
    print(lala)
fp.close()

# Read in .log files from samtools script output to generate lists of aligned read counts

libraries = []
scer_counts = []
spom_counts =[]
# Change seconds number in range() to equal to the number of lines in the log files.
for i in range(0, 32, 2):
    file = open('rep4_counts.log', 
                mode='r')
    content = file.readlines()
    libraries.append(content[i].strip('\n'))
    scer_counts.append(int(content[i+1].strip('\n')))
    file.close()
    file = open('rep4_spikein_counts.log', 
                mode='r')
    content = file.readlines()
    spom_counts.append(int(content[i+1].strip('\n')))
    file.close()
    
libraries
scer_counts
spom_counts

# Read lists into data frame
aligned_reads = pd.DataFrame(
    {
     "library": libraries,
     "scer_counts": scer_counts,
     "spom_counts": spom_counts
     }
    )

aligned_reads
aligned_reads[['spom_counts', 'scer_counts']]

# Do some useful math and create new dataframe columns (from MNase-seq)
aligned_reads["total_counts"] = aligned_reads["spom_counts"] + aligned_reads["scer_counts"]
# aligned_reads["spom / scer"] = aligned_reads["spom_counts"] / aligned_reads["scer_counts"]
aligned_reads["proportion_spom"] = aligned_reads["spom_counts"] / aligned_reads["total_counts"]
aligned_reads["proportion_scer"] = aligned_reads["scer_counts"] / aligned_reads["total_counts"]
# aligned_reads["1 / proportion_spom"] = 1 / aligned_reads["proportion_spom"]


# Plot a stacked boxplot of the proportions of reads mapped to Spom & Scer genomes
aligned_reads[["library", "proportion_spom", "proportion_scer"]].plot(
    x = 'library',
    xlabel = 'proportion reads mapped',
    xlim = (0,1),
    kind = 'barh',
    stacked = True,
    figsize = (5,10),
    legend = True,
    title = 'Proportion of reads mapped to S. pombe \nor S. cerevisiae genomes',
    )

### Math from James Chuang's ChIP-seq spike in notes:
#   exp = Scer
#   spike = Spom
#   alpha_IP = 1/(reads_IP_spike*(reads_input_exp/reads_input_spike))
#   reads_input_exp = aligned_reads.loc[aligned_reads["library"].str.contains('input')]["scer_counts"]
#   reads_input_spike = aligned_reads.loc[aligned_reads["library"].str.contains('input')]["spom_counts"]

# So normalization factor should be:
norm = aligned_reads.loc[aligned_reads["library"].str.contains('input')]["scer_counts"] / aligned_reads.loc[aligned_reads["library"].str.contains('input')]["spom_counts"]
aligned_reads.loc[0:3, 'alpha_IP'] = 1/(aligned_reads.loc[aligned_reads["library"].str.contains('93_D')]["spom_counts"]*norm[2])
aligned_reads.loc[4:7, 'alpha_IP'] = 1/(aligned_reads.loc[aligned_reads["library"].str.contains('93_I')]["spom_counts"]*norm[6])
aligned_reads.loc[8:11, 'alpha_IP'] = 1/(aligned_reads.loc[aligned_reads["library"].str.contains('95_D')]["spom_counts"]*norm[10])
aligned_reads.loc[12:15, 'alpha_IP'] = 1/(aligned_reads.loc[aligned_reads["library"].str.contains('95_I')]["spom_counts"]*norm[14])

# convert scintific notation into float
for i in range(len(aligned_reads['alpha_IP'])):
    aligned_reads.loc[i,'alpha_IP_float'] = format(aligned_reads.loc[i, 'alpha_IP'], '.16f')

#check numbers
aligned_reads[['library','alpha_IP_float']]


# Run below command to export
aligned_reads[["library", "alpha_IP_float"]].to_csv(path_or_buf='normalization_table.csv', index=False, header=False)

