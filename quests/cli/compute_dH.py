import os
import gc
import sys
import json
import time

import click
import numba as nb
import numpy as np

from .log import format_time
from .log import logger
from .load_file import descriptors_from_file
from quests.descriptor import DEFAULT_CUTOFF
from quests.descriptor import DEFAULT_K
from quests.descriptor import get_descriptors
from quests.entropy import DEFAULT_BANDWIDTH
from quests.entropy import DEFAULT_BATCH
from quests.entropy import delta_entropy
from quests.tools.time import Timer


@click.command("dH")
@click.argument("test", required=1)
@click.argument("reference", required=1)
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
def dH(
    test,
    reference,
    cutoff,
    nbrs,
    bandwidth,
    jobs,
    batch_size,
    output,
    overwrite,
):
    if output is not None and os.path.exists(output) and not overwrite:
        logger(f"Output file {output} exists. Aborting...")
        sys.exit(0)

    if jobs is not None:
        nb.set_num_threads(jobs)

    x, _ = descriptors_from_file(test, nbrs, cutoff)
    ref, _ = descriptors_from_file(reference, nbrs, cutoff)

    logger("Computing dH...")
    with Timer() as t:
        delta = delta_entropy(x, ref, h=bandwidth, batch_size=batch_size)
    entropy_time = t.time
    logger(f"dH computed in: {format_time(entropy_time)}")

    if output is not None:
        results = {
            "reference_file": reference,
            "test_file": test,
            "test_envs": x.shape[0],
            "ref_envs": ref.shape[0],
            "k": nbrs,
            "cutoff": cutoff,
            "bandwidth": bandwidth,
            "jobs": jobs,
            "delta_entropy": list(delta),
        }

        with open(output, "w") as f:
            json.dump(results, f, indent=4)
