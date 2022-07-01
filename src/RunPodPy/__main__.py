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
from munch import Munch
from ruamel.yaml import YAML

from cli import list_pods
from runpod import RunPod

logger = logger.opt(colors=True)


def configure_logging(config):
    logger.remove()
    if config.debug == True:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="INFO")


async def main(config: Munch, command):
    """Main function"""
    global RUNPOD_API_KEY
    RUNPOD_API_KEY = (
        RUNPOD_API_KEY
        if config.runpod_api["API_KEY"] is None
        else config.runpod_api["API_KEY"]
    )

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Register On Runpod",
        usage="python3 register_on_runpod.py <command> <command args>",
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
        default="configs/runpod_config.yaml",
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
        "--podName",
        type=str,
        help="Pod name to create",
        required=False,
        default=None,
    )
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
        "--gpuTypeId",
        type=str,
        help='The GPU type to use. e.g. "NVIDIA GeForce RTX 3080 Ti"',
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--imageName",
        type=str,
        help="The docker image to use",
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--volumePath",
        type=str,
        help="The volume path to mount",
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--args",
        type=str,
        help='The arguments to pass to docker. e.g. "bash -c "sleep infinity""',
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--containerDiskSize",
        type=int,
        help="The size of the container disk (GB)",
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--volumeSize",
        type=int,
        help="The size of the volume (GB)",
        required=False,
        default=None,
    )
    create_parser.add_argument(
        "--gpuCount",
        type=int,
        help="The number of GPUs to use",
        required=False,
        default=None,
    )

    list_parser = command_parsers.add_parser("list", help="List pods")

    register_parser = command_parsers.add_parser("register", help="""Register hotkey""")
    register_parser.add_argument(
        "--max_bid", type=float, required=True, help="""Max bid"""
    )
    register_parser.add_argument(
        "--spot", action="store_true", default=True, help="""Spot"""
    )
    register_parser.add_argument(
        "--coldkey",
        dest="coldkey",
        type=str,
        required=True,
        help="""Coldkey to register from""",
    )
    register_parser.add_argument(
        "-k",
        "--hotkeys",
        dest="hotkeys",
        type=str,
        nargs="*",
        required=False,
        action="store",
        help="A list of hotkeys to register",
    )
    register_parser.add_argument(
        "--ip_address",
        dest="ip_address",
        type=str,
        required=False,
        help="""IP address of the instance to use, otherwise a new one will be created""",
    )
    register_parser.add_argument(
        "--runpod_api_key",
        dest="runpod_api_key",
        type=str,
        required=False,
        help="""Runpod API key""",
    )

    config = Munch(parser)

    yaml = YAML()
    # Load config file into config
    with open(config.config_file, "r") as config_file:
        config.update(yaml.load(config_file))

    commands = {
        "register": register,
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
        asyncio.run(main(config, commands[config.command]))
    else:
        parser.print_help()
        exit(1)
