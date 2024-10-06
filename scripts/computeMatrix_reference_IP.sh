#!/bin/bash

#SBATCH --partition=short                      # Partition to run in
#SBATCH -c 1                                 # Requested cores
#SBATCH --time=0-00:20                    # Runtime in D-HH:MM format
#SBATCH --mem=200M                           # Requested Memory
#SBATCH -o %j.out                            # File to which STDOUT will be written, including job ID (%j)
#SBATCH -e %j.err                            # File to which STDERR will be written, including job ID (%j)
#SBATCH --mail-type=ALL                      # ALL email notification type
#SBATCH --mail-user=james_warner@hms.harvard.edu          # Email to which notifications will be sent


module load gcc/9.2.0 python/3.9.14 deeptools/3.5.0

for IP in V5 8WG16 Flag; do

computeMatrix reference-point -S deeptools/si/*${IP}*_${1%}_si.bw -R genome/annotations/Scer_transcripts_w_verifiedORFs-nonoverlapping.bed -o deeptools/si/${IP}_${1%}_si_IP_reference.gz \
	--outFileNameMatrix deeptools/si/tab/${IP}_${1%}_si_IP_reference.tab \
	-a 4500 \
	-b 250 \
	-bs 10 \
	--averageTypeBins mean \

done
