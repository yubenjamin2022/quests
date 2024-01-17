import json
import os
import sys
import time
from typing import List

import click
import numba as nb
import numpy as np
from ase import Atoms
from ase.io import read

from .log import format_time
from .log import logger
from quests.descriptor import DEFAULT_CUTOFF
from quests.descriptor import DEFAULT_K
from quests.descriptor import get_descriptors
from quests.entropy import DEFAULT_BANDWIDTH
from quests.entropy import DEFAULT_BATCH
from quests.entropy import get_bandwidth
from quests.entropy import perfect_entropy
from quests.tools.time import Timer


def sample_indices(size: int, n: int):
    if size < n:
        return np.arange(0, size, 1, dtype=int)

    return np.random.randint(0, size, n)


def get_sampling_fn(dset: List[Atoms], x: np.ndarray, sample, sample_dataset):
    if not sample_dataset:
        # sample environments
        def sample_items():
            indices = sample_indices(len(x), sample)
            return x[indices]
        
        return sample_items

    # create indices for the dataset
    start = 0
    dset_indices = []
    for i, atoms in enumerate(dset):
        num_atoms = len(atoms)
        idx = np.arange(start, start + num_atoms, 1, dtype=int)
        dset_indices.append(idx)
        start = start + num_atoms

    def sample_items():
        indices = sample_indices(len(dset_indices), sample) 
        x_indices = np.concatenate([
            dset_indices[i] for i in indices
        ])
        return x[x_indices]

    return sample_items


@click.command("entropy_sampler")
@click.argument("file", required=1)
@click.option(
    "-c",
    "--cutoff",
    type=float,
    default=DEFAULT_CUTOFF,
    help=f"Cutoff (in Å) for computing the neighbor list (default: {DEFAULT_CUTOFF:.1f})",
)
@click.option(
    "-k",
    "--nbrs",
    type=int,
    default=DEFAULT_K,
    help=f"Number of neighbors when creating the descriptor (default: {DEFAULT_K})",
)
@click.option(
    "-b",
    "--bandwidth",
    type=float,
    default=DEFAULT_BANDWIDTH,
    help=f"Bandwidth when computing the kernel (default: {DEFAULT_BANDWIDTH})",
)
@click.option(
    "--estimate_bw",
    is_flag=True,
    default=False,
    help="If True, estimates the bandwidth based on the density",
)
@click.option(
    "-s",
    "--sample",
    type=int,
    default=1000,
    help="If given, takes a sample of the environments before computing \
            its entropy (default: uses the entire dataset)",
)
@click.option(
    "--sample_dataset",
    is_flag=True,
    default=False,
    help="If True, subsamples the dataset as opposed to the environment.",
)
@click.option(
    "-n",
    "--num_runs",
    type=int,
    default=20,
    help="Number of runs to resample (default: 20)",
)
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=None,
    help="Number of jobs to distribute the calculation in (default: all)",
)
@click.option(
    "--batch_size",
    type=int,
    default=DEFAULT_BATCH,
    help=f"Size of the batches when computing the distances (default: {DEFAULT_BATCH})",
)
@click.option(
    "-o",
    "--output",
    type=str,
    default=None,
    help="path to the json file that will contain the output\
            (default: no output produced)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="If True, overwrite the output file",
)
def entropy_sampler(
    file,
    cutoff,
    nbrs,
    bandwidth,
    estimate_bw,
    sample,
    sample_dataset,
    num_runs,
    jobs,
    batch_size,
    output,
    overwrite
):
    if output is not None and os.path.exists(output) and not overwrite:
        logger(f"Output file {output} exists. Aborting...")
        sys.exit(0)

    if jobs is not None:
        nb.set_num_threads(jobs)

    logger(f"Loading and creating descriptors for file {file}")
    dset = read(file, index=":")

    with Timer() as t:
        x = get_descriptors(dset, k=nbrs, cutoff=cutoff)
    descriptor_time = t.time
    logger(f"Descriptors built in: {format_time(descriptor_time)}")
    logger(f"Descriptors shape: {x.shape}")

    if estimate_bw:
        volume = np.mean([at.get_volume() / len(at) for at in dset])
        bandwidth = get_bandwidth(volume)

    # if dataset is smaller than sample, no need to
    # run multiple times
    if len(x) <= sample:
        num_runs = 1

    # determine how the dataset is going to be sampled
    sample_items = get_sampling_fn(dset, x, sample, sample_dataset)

    # compute the entropy `num_runs` times
    entropies = []
    entropies_times = []
    for n in range(num_runs):
        xsample = sample_items()
        with Timer() as t:
            entropy = perfect_entropy(xsample, h=bandwidth, batch_size=batch_size)
        entropy_time = t.time

        entropies.append(entropy)
        entropies_times.append(entropy_time)

    logger(f"Entropy: {np.mean(entropies): .3f} ± {np.std(entropies): .3f} (nats)")
    logger(f"computed from {num_runs} runs.")
    logger(f"Max theoretical entropy: {np.log(xsample.shape[0]): .3f} (nats)")

    # log the results
    if output is not None:
        results = {
            "file": file,
            "n_envs": x.shape[0],
            "k": nbrs,
            "cutoff": cutoff,
            "bandwidth": bandwidth,
            "jobs": jobs,
            "sample": sample,
            "sample_dataset": sample_dataset,
            "num_runs": num_runs,
            "entropies": entropies,
            "descriptor_time": descriptor_time,
            "entropies_times": entropies_times,
        }

        with open(output, "w") as f:
            json.dump(results, f, indent=4)
