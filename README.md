![Alt text](Flexpert_logo.png)

# Flexpert: "Learning to engineer protein flexibility"

[![ICLR badge](https://img.shields.io/badge/ICLR-2025-brown.svg)](https://openreview.net/forum?id=L238BAx0wP)
[![arXiv badge](https://img.shields.io/badge/arXiv-2310.18515-b31b1b.svg?color=blue)](https://arxiv.org/abs/2412.18275)


This repository accompanies the ICLR 2025 paper ["Learning to engineer protein flexibility"](https://arxiv.org/abs/2412.18275) by Petr Kouba, Joan Planas-Iglesias, Jiri Damborsky, Jiri Sedlar, Stanislav Mazurenko, Josef Sivic. 

The repository presents the training and inference code for the Flexpert-3D and Flexpert-Seq models, as well as the Flexpert-Design model. Furthermore some scripts on preparing the datasets are provided together with links to download the data and the trained weights. If you find this repository useful in your work, please see the section "References" to learn how to reference our paper and other work related to this repository.

## Environment

Tested for Python 3.9. For other versions enviroment might need to be adapted.

The `requirements.txt` file in the root directory can be used to create your Python environment for Flexpert-3D, Flexpert-Seq and the analysis of the flexibility metrics. Separate requirements are provided for Flexpert-Design in the respective directory.

```
pip install -r requirements.txt
```

Alternatively, use the Docker (Singularity) images with PyTorch, PyTorch Geometric and Pytorch Lightning built for (i) NVIDIA GPUs (CUDA), (ii) AMD GPUs (ROCm), see example below:

```
#Set environment variables for singularity cache, it should be on a disc with enough free space (tens of GB) - the provided path is an example which works well for our cluster
export SINGULARITY_TMPDIR=/tmp/USERNAME
export SINGULARITY_CACHEDIR=/tmp/USERNAME

#For AMD GPUs pull this image:
singularity pull docker://koubic/lumi-pyg-lightning-tk:latest

#For GPUs with CUDA support pull this:
singularity pull docker://koubic/karolina_cuda_pyg:latest

#On the GPU node (e.g. after allocating interactive job on a GPU node), activate the singularity container e.g. like this (mounting the /scratch drive, mount the directory relevant for you):
singularity exec -B /scratch/:/scratch/ lumi-pyg-lightning-tk_latest.sif bash 

#When using the other container in case of CUDA machine, run
singularity exec -B /scratch/:/scratch/ --nv karolina_cuda_pyg_latest.sif bash 
```

Some packages might still be missing, but the crucial packages depending on the GPU drivers should work properly. The missing packages can be installed with pip.

Note: In our environment, Python is called "python3" thats why we use it in the commands. For different users it might be called just "python".

## Data

This section provides details on reproducing the training and prediction datasets used in the paper. For running the flexibility predictions using Flexpert-3D and Flexpert-Seq, this section might be skipped, although it discusses some scripts which might be useful for preparing the inputs to the Flexpert-3D and Flexpert-Seq models.

The preprocessed [ATLAS](https://www.dsimb.inserm.fr/ATLAS/download.html) dataset with topology splits is provided in the folder `data/`. To prepare your own dataset, see following example:

1) Paths for input PDBs and for output directory where to store preprocessed data can be set in `configs/data_config.yaml`.

2) Inside `data/PDBs` place the PDB files of the proteins you want in your dataset. We provide 10 example PDBs from the ATLAS dataset in this repo. The PDB files should be named according to the ATLAS dataset naming convention: PDBCODE_CHAINCODE.pdb (e.g. 1ah7_A.pdb).

3) Run:

``` 
python3 data/scripts/prepare_dataset.py
```

This prepares the `chain_set.jsonl` file, based on the PDB files. Most importantly, it extracts the sequence and the backbone coordinates.

4) Run:

```
python3 data/scripts/get_enm_fluctuations_for_dataset.py --enm ANM
```

This computes the Elastic Network Models (ENM) estimation of per-residue fluctuations for the input dataset. The paths to input file (backbones_dataset_path) and where to output the files with the computed fluctuations are set in `configs/data_config.yaml`. This example uses Anisotropic Network Models (ANM) in particular, but it can also run with Gaussian Network Models (GNM) when specified by the argument.

Alternatively, when specified in the configs, it can also read a .csv file on the input containing paths to PDB files and compute the ENM from there, without the precomputed `chain_set.jsonl` file.


### Reproduction of the dataset of RMSF labels from the ATLAS dataset:
**Update: Please note that ATLAS has switched to reporting RMSF in Angstroms, before it was nanometers, so Flexpert is trained in nanometers and its raw outputs correspond to nanometers.**
This can take few hours and a significant disc space, as it calls the ATLAS dataset API, downloads the data (including the MD simulations), unzips the data and stores it. It is not necessary to run it for the reproduction as we already provide the preprocessed ATLAS in the repo. If you are building your own dataset, this might be irrelevant, unless your proteins of interest are included in the ATLAS dataset.

To download ATLAS dataset (in order to obtain the RMSF labels for the training), run the following command:

```
python3 data/atlas/download_analyses.py
```

To extract the RMSF labels from the ATLAS dataset run:

```
python3 data/scripts/extract_rmsf_labels.py
```

Paths for input / output for the RMSF label extraction can be modified in `configs/data_config.yml`.

If you use the ATLAS dataset, please cite the [paper](https://academic.oup.com/nar/article/52/D1/D384/7438909?login=false) by Meersche et al.

## Training Flexpert-Seq and Flexpert-3D

This section provides details on reproducing the training of Flexpert-Seq and Flexpert-3D models, it might be skipped if you are only interested in running the predictions.

Inside `config/` review the 3 config files: 

1) `lora_config.yaml` contains the default LoRA parameters, from this repo (and corresponding paper). Leave this as it is unless you want to make your own experiments.
2) `train_config.yaml` contains arguments to reproduce the training. It can be changed to experiment, alternatively most of these arguments can be overriden by arguments passed to the `train.py` script. See `python3 train.py --help` for the arguments which can be provided directly to the script.
3) `env_config.yaml` use this to set cache path for HuggingFace models or to set name of wandb project.

Run the training:
```
#For training Flexpert-Seq:
python3 train.py --run_name testrun-Seq --adaptor_architecture no-adaptor

#For training Flexpert-3D:
python3 train.py --run_name testrun-3D --adaptor_architecture conv
```

The code for the LoRA fine-tuning of protein language models is derived from [this repo](https://github.com/agemagician/ProtTrans/tree/master/Fine-Tuning) accompanying the [paper](https://www.nature.com/articles/s41467-024-51844-2) "Fine-tuning protein language models boosts predictions across diverse tasks" by Schmirler et al.

## Inference with Flexpert-Seq and Flexpert-3D

To run the predictions, make sure you have the weights for the models you want to use. These can be obtained either by training the models yourself following the above section or by downloading the weights using the following script:

```
. download_flexpert_weights.sh
```

Example predictions of flexibility, input is provided by fasta, jsonl, pdb file or a list of paths to PDB files. 

- For fasta and jsonl the output is a txt file with the predicted flexibility profiles. 

- For PDB input the output is a new PDB with the predicted flexibility written inside the B-factor column. 

- For a list of PDB files the outputs are multiple PDB files with the predicted flexibility written inside the B-factor column. 

- When provided the `--output_enm` flag in case of Flexpert-3D, the variant of the outputs with ENM predicted flexibilities is also produced.

- By specifying the flags `--splits_file` and `--split` the prediction is performed for a particular split of the dataset (with the dataset being provided as an input_file).

- By specifying the `--output_fasta` flag, the sequences used for the prediction are outputted in a fasta file. This can be useful e.g. when working with a list of PDB files as input, when there was no fasta file provided.

```
#For Flexpert-Seq (using fasta on the input):
python3 predict.py --modality SEQ --input_file data/example_sequences.fasta 

#For Flexpert-3D (using preprocessed jsonl file on the input containing sequences and structures):
python3 predict.py --modality 3D --input_file data/custom_dataset/chain_set.jsonl

#For Flexpert-3D / Flexpert-Seq (using PDB on the input):
python3 predict.py --modality 3D --input_file data/PDBs/1ah7_A.pdb
python3 predict.py --modality SEQ --input_file data/PDBs/1ah7_A.pdb
```

Example prediction (and also reproduction of the reported results in the paper) for a particular split of a dataset, which reads whole dataset and the train/val/test splits and performs prediction for the test split:

```
python3 predict.py --modality SEQ --input_file data/atlas_sequences.fasta --splits_file data/atlas_splits.json --split test

python3 predict.py --modality 3D --input_file data/atlas_minimized_fluctuations_ANM.jsonl --splits_file data/atlas_splits.json --split test
```

Example prediction for a single PDB file and for a list of PDB files with Flexpert-3D, asking to also obtain a separate output with ENM predicted flexibilities, customizing the name of the output files:

```
python3 predict.py --modality 3D --input_file data/PDBs/1ah7_A.pdb --output_enm --output_name 1ah7_test

python3 predict.py --modality 3D --input_file data/PDBs/paths.pdb_list --output_enm --output_name test_output
```

Tip: when using terminal outside of the singularity container, you can generate a textfile with all the paths to the PDB files in `data/PDBs/` using something like: `realpath data/PDBs/*.pdb > data/PDBs/paths.pdb_list`.

## Analysis of the flexibility metrics

To reproduce the numbers in the Tables 1-3 of the paper, run the commands below. You may need to first download the ATLAS dataset following the instructions above to get the data for AF2 pLDDT and B-factors.

```
#this will give you Table 1 of the paper, running evaluation over whole ATLAS dataset (skipping 7 out of 1390 proteins due to undefined correlations)
python3 get_correlation_analysis.py

#this will give you superset of the results reported in Tables 2-3 of the paper, running evaluation over the test split of the ATLAS dataset
python3 get_correlation_analysis.py --evaluate_flexpert 
```

## Flexpert-Design

To run Flexpert-Design, go to the `Flexpert-Design` directory and follow the instructions in the `README.md` file there:

```
cd Flexpert-Design
```

## References

If you find this repository useful in your work, please cite our paper:

```
@inproceedings{
kouba2025learning,
title={Learning to engineer protein flexibility},
author={Petr Kouba and Joan Planas-Iglesias and Jiri Damborsky and Jiri Sedlar and Stanislav Mazurenko and Josef Sivic},
booktitle={The Thirteenth International Conference on Learning Representations},
year={2025},
url={https://openreview.net/forum?id=L238BAx0wP}
}
```

Also consider citing the respective papers if you use the [ATLAS MD dataset](https://academic.oup.com/nar/article/52/D1/D384/7438909), the LoRA fine-tuning of protein language models ([Fine-tuning protein language models boosts predictions across diverse tasks](https://www.nature.com/articles/s41467-024-51844-2)) or the training of the inverse folding models inside Flexpert-Design ([ProteinInvBench](https://papers.nips.cc/paper_files/paper/2023/hash/d73078d49799693792fb0f3f32c57fc8-Abstract-Datasets_and_Benchmarks.html)).


