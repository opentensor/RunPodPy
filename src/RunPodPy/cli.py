# The MIT License (MIT)
# Copyright © 2022 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import json
from typing import List

import loguru
from munch import Munch
from tabulate import tabulate

from runpod import RunPod, RunPodException, RunPodInstance


async def stop(runpod: RunPod, config: Munch, logger: loguru.Logger) -> None:
    """Stops the instance(s)"""
    # Check runpod API connection
    if not await runpod.test_connection(logger):
        raise RunPodException("Runpod API is not connected")

    if config.get("podId") is not None:
        # Stop the pod
        await runpod.stop_instance(config.podId, logger)
        logger.info(f"Stopped pod {config.podId}")

    elif config.all:
        logger.info("Stopping all pods")
        # Stop all pods
        pods = await runpod.get_pods(logger)
        for pod in pods:
            await runpod.stop_instance(pod.podId, logger)
            logger.info(f"Stopped pod {pod.podId}")
        logger.info("DONE | Stopped all pods")
    else:
        logger.error("No --podId or --all specified")


async def start(runpod: RunPod, config: Munch, logger: loguru.Logger) -> None:
    """Starts the instance(s)"""
    # Check runpod API connection
    if not await runpod.test_connection(logger):
        raise RunPodException("Runpod API is not connected")

    spot: bool = config.spot

    if config.get("podId") is not None:
        # Get the pod
        pod: RunPodInstance = await runpod.get_pod_by_id(config.podId, logger)
        if pod is None:
            logger.error(f"Pod {config.podId} not found")
            return False
        # Start the pod
        await runpod.start_instance(pod.podId, pod.gpuCount, logger, config.max_bid, spot)
        logger.info(f"Started pod {config.podId}")

    elif config.all:
        logger.info("Starting all pods")
        # Get all pods
        pods = await runpod.get_pods()
        for pod in pods:
            # Start the pod
            await runpod.start_instance(pod.podId, pod.gpuCount, logger, config.max_bid, spot)
            logger.info(f"Started pod {pod.podId}")
        logger.info("DONE | Started all pods")
    else:
        logger.error("No --podId or --all specified")


async def create(runpod: RunPod, config: Munch, logger: loguru.Logger) -> None:
    """Creates a runpod instance"""
    # Check runpod API connection
    if not await runpod.test_connection(logger):
        raise RunPodException("Runpod API is not connected")

    config.machine = config["machine_defaults"].copy()

    for key in config["machine_defaults"]:
        if config.get(key) is None:
            continue
        else:
            config.machine[key] = config[key]

    config.machine["args"] = json.dumps(config.machine["args"])

    if config.get("podName") is None:
        # Get all the pods
        pods = await runpod.get_pods(logger)

        # Get name for pod
        podName: str = config["machine"]["gpuTypeId"].replace(" ", "_") + str(len(pods))
    else:
        podName: str = config.podName

    config.machine["podName"] = podName

    # Create a pod if there are no pods
    pod = await runpod.create_instance(config.max_bid, config, logger, spot=config.spot)
    if pod is None:
        logger.error(
            f"Failed to create pod - max_bid:{config.max_bid} spot:{config.spot}"
        )
    else:
        logger.info(f"Created pod {pod.podId}")


async def destroy(runpod: RunPod, config: Munch, logger: loguru.Logger) -> None:
    """Destroys the instance(s)"""
    # Check runpod API connection
    if not await runpod.test_connection(logger):
        raise RunPodException("Runpod API is not connected")

    if config.get("podId") is not None:
        # Destroy the pod
        await runpod.destroy_instance(config.podId, logger)
        logger.info(f"Destroyed pod {config.podId}")

    elif config.all:
        logger.info("Destroying all pods")
        # Destroy all pods
        pods = await runpod.get_pods(logger)
        for pod in pods:
            await runpod.destroy_instance(pod.podId, logger)
            logger.info(f"Destroyed pod {pod.podId}")
        logger.info("DONE | Destroyed all pods")
    else:
        logger.error("No --podId or --all specified")


async def list_pods(runpod: RunPod, config: Munch, logger: loguru.Logger) -> None:
    """Lists the instance(s)"""
    # Check runpod API connection
    if not await runpod.test_connection(logger):
        raise RunPodException("Runpod API is not connected")

    logger.info("Connected to RunPod API")

    pods = await runpod.get_pods(logger)

    if len(pods) == 0:
        logger.info("No pods found")
    else:
        table: List[List[str]] = [
            [
                "podId",
                "podName",
                "instanceType",
                "gpuTypeId",
                "gpuCount",
                "costPerHr",
                "ip_address",
            ]
        ]
        table.extend(
            [
                [
                    pod.podId,
                    pod.podName,
                    "SPOT" if pod.spot else "ON_DEMAND",
                    pod.gpuDisplayName,
                    pod.gpuCount,
                    pod.cost,
                    pod.ip_address,
                ]
                for pod in pods
            ]
        )
        logger.info(f"Found {len(pods)} pods:\n{tabulate(table, headers='firstrow')}")
