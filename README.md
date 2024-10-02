
# ChIP-seq analysis pipeline

## description

An analysis pipeline for paired-end ChIP-seq data with the following major steps:

- alignment with [bowtie2](https://bowtie-bio.sourceforge.net/bowtie2/manual.shtml) (.bam)
- indexing and sorting alignment files with [samtools](http://www.htslib.org/) (.bam and .bai)
- summary of fragment sizes with [deeptools PEFragmentSize](https://deeptools.readthedocs.io/en/develop/content/tools/bamPEFragmentSize.html)
- counting reads aligning to experimental (S. cerevisiae) and spike-in (S.pombe) genomes with [samtools view](http://www.htslib.org/doc/samtools-view.html)
- calculation of per-library spike-in normalization scaling factors using a custom python script
- generation of coverage tracks (.bw) scaled by spike-in normalization using [deeptools bamCoverage](https://deeptools.readthedocs.io/en/develop/content/tools/bamCoverage.html)
- log2 fold enrichment of IP over input coverage (.bw) using [deeptools bigwigCompare](https://deeptools.readthedocs.io/en/develop/content/tools/bigwigCompare.html)
- generation of matrices for plotting scaled coverage data using deeptools (.gz) or directly in python (.tab) using [deeptools computeMatrix](https://deeptools.readthedocs.io/en/develop/content/tools/computeMatrix.html#reference-point)
- data visualization ([heatmaps](https://deeptools.readthedocs.io/en/develop/content/tools/plotHeatmap.html) and [metagenes](https://deeptools.readthedocs.io/en/develop/content/tools/plotProfile.html)) using deeptools plotting functions and custome python scripts

## requirements

- designed to be run on O2, the high-performance computing cluster at HMS
- uses slurm job scheduler to batch submit jobs
- Paired-end FASTQ files from ChIP-seq libaries
	- FASTQ files should be demultiplexed and can (should) be compressed (.gz)
	- FASTQ filenames are used by the scripts throughout this pipeline, and should easily identify the sample. For example, my filenames usually take the format: strain_treatment_IP_replicate (e.g. 93_D_8WG16_rep2). After demultiplexing, there is usually trailing info added to the filename: e.g. _S8_R1_001.fastq.gz. The S indicates the index number on your sample sheet, R1 and R2 indicate the paired reads from the sequencer, and 001 is a trailing number added for reasons beyond my comprehension.
- FASTA files for genome alignment, included for S. cerevisiae and S. pombe in the 'genomes/bowtie2_index/' directory in this repository.
- BED files to tell deeptools which portions of the genome you would like to plot. I have included the standard non-overlapping ORF BED file from James Chuang in the 'genomes/annotations/' directory of this repository.
- Some patience. It will likely take some troubleshooting and path editing in the slurm scripts to analyze your data. My goal is to make this process as pain-free as possible, so I will try to explain how each step functions so that you can debug with confidence.

## instructions

**1. Clone this repository into a clean directory on O2.**

```bash
# clone the repository
git clone https://github.com/jamwarner/chip_seq.git

# navigate to the newly created directory
cd chip_seq
```


**2. Download or transfer your .fastq.gz files into the 'fastq/' directory.**

**3. Align your libraries to the experimental and spike-in genomes.**

Run all commands from the root 'chip_seq' directory.

We will submit two alignment jobs for each library: one to the experimental genome and the othe to the spike-in genome. Submitting the jobs separately allows all of the alignments to run in parallel.

```bash
# use a for loop to submit alignments for each set of paired reads separately
for name in fastq/*R1_001.fastq.gz; do sbatch scripts/batch_aligner.sh $name; done
for name in fastq/*R1_001.fastq.gz; do sbatch scripts/spike_batch_aligner.sh $name; done
```

This will generate two sets (experimental and spike-in) of three files for each library:
- in bam/
	- filename_unsorted.bam
	- filename_sorted.bam
	- filename_sorted.bam.bai
- in bam/spike-in/
	- filename_spikein_unsorted.bam
	- filename_spikein_sorted.bam
	- filename_spikein_sorted.bam.bai

```bash
# check to see if the alignment files are there
ls bam/
ls bam/spike-in
```

Also generated is a summary of each alignment in the logs/ directory:
- filename_bowtie2.txt

```bash
# take a peek
vim logs/<FILE_NAME>_bowtie2.txt
```

We will use the 'sorted.bam' and 'sorted.bam.bai' files in subsequent steps. I don't think tha the 'unsorted.bam' files need to be saved, but I have not made a habit of deleting them.

**4. Determine the distribution of insert sizes in your ChIP samples (since the reads are paired, we can determine the size of each fragment that was sequenced from its two ends).**

```bash
# use deeptools to generate summary statistics for each sorted.bam file
sbatch scripts/bamPEFragmentSize.sh
```

This script will look at all of the 'sorted.bam' files and will generate two new files in the 'fragment_sizes/' directory:
- a histogram showing the distribution of the insert sizes for each library
- a CSV file with this information in tabular format. This is usually easier to interpret.

These files will be generated for the experimental and spike_in alignments separately.

**5. Count aligned reads for experimental and spike-in genomes.**

This step uses [samtools view](http://www.htslib.org/doc/samtools-view.html) to count the number of reads in each 'sorted.bam' file. 
- -c makes samtools output only the count and not the reads themselves
- -F filters the BAM files to EXCLUDE reads that fit the [flag condition](https://broadinstitute.github.io/picard/explain-flags.html)
	- the flag here is '388' which = unmapped OR not primary alignment OR second in pair (which confirms read pairs are only counted once and not twice)

What the script looks like:

> ```bash
> for name in /bam/*_sorted.bam; do
> 	(basename ${name} _sorted.bam) >> /logs/experimental_counts.log
> 	samtools view -c -F 388 ${name} >> /logs/experimental_counts.log
> done
> ```

To run:

```bash
sbatch scripts/read_counter.sh
```

This scripts creates two files in the 'logs/' directory: 'experimental_counts.log' and 'spikein_counts.log'. These files contain pairs of lines:
- the first line is the BAM filename with '_sorted.bam' stripped
- the second line is the number of paired reads that are mapped to the respective genome in each 'sorted.bam' file
The lines continue to alternate for each BAM file processed.

**6. Do spike-in normalization math.**

Spike-in normalization math is not intuitive (at least it isn't to me). I have included a PDF ('chip_spikeins.pdf') in this repository that was written by James Chuang and explains all of the logic and algebra behind this step. In short, the 'input' libraries allow us to empirically determine the proportion of experimental to spike-in material that went into each IP. 

Essentially, if we wanted to normalize the experimental input signal between libraries, we could just normalize by library size (number of experimental reads). Scaling by library size does not work for the IPs, however, as getting half as many experimental reads is meaningful (as long as the number of spike-in reads is the same). Therefore, if we use the spike-in reads to "link" the IP and input samples, we can scale each IP to the same scale as the input signal. Then you can calculate the IP enrichment over input, which is exactly what we want to do! (And is what we do in step 8.)

At this point, I transfer these two '_counts.log' files to my computer and use a custom python script that I have written to determine the scaling factors to use for spike-in normalization. I plan to move this script into this repository and edit it so that it can be run on O2 instead of needing to run it locally. This python script may need extensive editing to make it work for your total number of samples, as well as for your number of IPs per input.

The output of this step is a file called 'normalization_table.csv' that consists of two columns:
- column 1 is the library name
- column 2 is the scaling factor that will be used for normalization

Currently, after this CSV is generated, I manually transfer it back to O2 and place it in the 'logs/' directory. Running the script locally on O2 will also make this second transfer unnecessary.

**7. Generate coverage tracks for each library scaled by spike-in normalization.**




