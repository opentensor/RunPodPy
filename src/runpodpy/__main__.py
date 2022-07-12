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

import argparse
import asyncio
import sys

from gql.transport.aiohttp import AIOHTTPTransport
from loguru import logger
from ruamel.yaml import YAML
import runpodpy

from runpodpy.cli import create, destroy, list_pods, start, stop
from runpodpy.runpod import RunPod
from runpodpy.config import Config, config_builder
from runpodpy import CloudType, GPUTypeId

logger = logger.opt(colors=True)


def configure_logging(config):
    logger.remove()
    if config.debug == True:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="INFO")


async def run_command(config: Config, command):
    """Main function"""
    global RUNPOD_API_KEY
    if config.runpod_api.get('API_KEY') is None:
        raise ValueError('No API_KEY found in config.runpod_api')
        
    RUNPOD_API_KEY = config.runpod_api["API_KEY"]

    # Connect to runpod api
    runpod_transport = AIOHTTPTransport(
        url=f"{config.runpod_api['URL']}?api_key={RUNPOD_API_KEY}",
        headers={
            "content-type": "application/json",
        },
    )

    # Setup runpod API
    runpod = RunPod(runpod_transport)

    if await runpod.test_connection(logger):
        logger.success("Connected to runpod api")

        await command(runpod, config, logger)
    else:
        logger.error("Failed to connect to runpod")
        exit(1)

def main():
    parser = argparse.ArgumentParser(
        description=f"RunPodPy v{runpodpy.__version__}",
        add_help=True,
    )
    parser._positionals.title = "commands"
    command_parsers = parser.add_subparsers(dest="command")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging", default=False
    )
    parser.add_argument(
        "--config_file",
        type=str,
        help="Path to config file",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--runpod_api.URL",
        "--URL",
        type=str,
        dest="runpod_api.URL",
        help="Base URL of runpod api",
        default="https://api.runpod.io/graphql",
        required=False,
    )
    parser.add_argument(
        "--runpod_api.API_KEY",
        "--API_KEY",
        type=str,
        dest="runpod_api.API_KEY",
        help="Your RunPod.io api key",
        required=False,
    )

    stop_parser = command_parsers.add_parser("stop", help="Stop a pod")
    stop_parser.add_argument(
        "--podId",
        type=str,
        help="Pod id to stop",
        required=False,
        default=None,
    )
    stop_parser.add_argument(
        "--all",
        action="store_true",
        help="Stop all pods",
        required=False,
        default=False,
    )

    destroy_parser = command_parsers.add_parser(
        "destroy", help="Destroy a pod", aliases=["terminate"]
    )
    destroy_parser.add_argument(
        "--podId",
        type=str,
        help="Pod id to destroy",
        required=False,
        default=None,
    )
    destroy_parser.add_argument(
        "--all",
        action="store_true",
        help="Destroy all pods",
        required=False,
        default=False,
    )

    start_parser = command_parsers.add_parser(
        "start", help="Start a pod", aliases=["run", "resume"]
    )
    start_parser.add_argument(
        "--podId",
        type=str,
        help="Pod id to start",
        required=False,
        default=None,
    )
    start_parser.add_argument(
        "--all",
        action="store_true",
        help="Start all pods",
        required=False,
        default=False,
    )
    start_parser.add_argument(
        "--max_bid",
        type=float,
        help="Maximum bid for the pod",
        required=False,
        default=None,
    )
    start_parser.add_argument(
        "--spot",
        action="store_true",
        help="Start the pod as a spot instance",
        required=False,
        default=False,
    )

    create_parser = command_parsers.add_parser("create", help="Create a pod")
    create_parser.add_argument(
        "--spot",
        action="store_true",
        help="Create the pod as a spot instance",
        required=False,
        default=False,
    )
    create_parser.add_argument(
        "--max_bid",
        type=float,
        help="Maximum bid for the pod",
        required=False,
        default=None,
    )    
    create_parser.add_argument(
        "--podName",
        "--machine.podName",
        dest="machine.podName",
        type=str,
        help="Pod name to create",
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--gpuTypeId",
        "--machine.gpuTypeId",
        dest="machine.gpuTypeId",
        type=GPUTypeId,
        choices=list(GPUTypeId),
        help='The GPU type to use. e.g. "NVIDIA GeForce RTX 3080 Ti"',
        required=False,
        default=GPUTypeId.RTX_3080_TI,
    )
    create_parser.add_argument(
        "--cloudType",
        "--cloud",
        dest="cloudType",
        type=CloudType,
        choices=list(CloudType),
        help='The CloudType to deploy to. e.g. COMMUNITY, SECURE',
        required=False,
        default=CloudType.COMMUNITY,
    )
    create_parser.add_argument(
        "--imageName",
        "--machine.imageName",
        dest="machine.imageName",
        type=str,
        help="The docker image to use",
        required=False,
        default='pytorch/pytorch',
    )
    create_parser.add_argument(
        "--volumePath",
        "--machine.volumePath",
        dest="machine.volumePath",
        type=str,
        help="The volume path to mount",
        required=False,
        default='/root',
    )
    create_parser.add_argument(
        "--args",
        "--machine.args",
        dest="machine.args",
        type=str,
        help='The arguments to pass to docker. e.g. "bash -c "sleep infinity""',
        required=False,
        default='bash -c "sleep infinity"',
    )
    create_parser.add_argument(
        "--containerDiskSize",
        "--machine.containerDiskSize",
        dest="machine.containerDiskSize",
        type=int,
        help="The size of the container disk (GB)",
        required=False,
        default=40,
    )
    create_parser.add_argument(
        "--volumeSize",
        "--machine.volumeSize",
        dest="machine.volumeSize",
        type=int,
        help="The size of the volume (GB)",
        required=False,
        default=40,
    )
    create_parser.add_argument(
        "--gpuCount",
        "--machine.gpuCount",
        dest="machine.gpuCount",
        type=int,
        help="The number of GPUs to use",
        required=False,
        default=1,
    )
    create_parser.add_argument(
        "--templateId",
        "--machine.templateId",
        dest="machine.templateId",
        type=str,
        help="The templateId to use",
        required=False,
        default=argparse.SUPPRESS,
    )

    list_parser = command_parsers.add_parser("list", help="List pods")

    config: Config = config_builder(parser)

    yaml = YAML()

    if config.config_file:
        # Load config file into config
        with open(config.config_file, "r") as config_file:
            config.update(yaml.load(config_file))

    commands = {
        "stop": stop,
        "destroy": destroy,
        "terminate": destroy,
        "start": start,
        "run": start,
        "resume": start,
        "create": create,
        "list": list_pods,
    }

    configure_logging(config)

    if config.command in commands.keys():
        # Run main with the command
        asyncio.run(run_command(config, commands[config.command]))
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    
    main()
