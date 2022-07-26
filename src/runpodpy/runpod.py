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

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional

import loguru
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError

from runpodpy import CloudType, GPUTypeId, PodStatus


class RunPodException(Exception):
    """RunPodException"""

    pass


class OutbidException(RunPodException):
    """OutbidException
    Raised when the bid for a spot instance is higher than the current bid.
    """

    pass


class RunPodInstance:
    """RunPodInstance"""

    ip_address: str = "ssh.runpod.io"
    gpuCount: int
    gpuDisplayName: GPUTypeId
    vcpuCount: int
    memoryInGb: int
    imageName: str
    podName: str
    cost: float
    podId: str
    podHostId: str
    spot: bool
    desiredStatus: PodStatus
    cloudType: CloudType

    def __init__(
        self,
        podName: str,
        cost: float,
        podId: str,
        podHostId: str,
        imageName: str,
        gpuDisplayName: GPUTypeId,
        gpuCount: int,
        vcpuCount: int,
        memoryInGb: int,
        cloudType: CloudType,
        desiredStatus: PodStatus,
        spot: bool = True,
    ):
        self.podName = podName
        self.cost = cost
        self.spot = spot
        self.podId = podId
        self.podHostId = podHostId
        self.gpuCount = gpuCount
        self.gpuDisplayName = gpuDisplayName
        self.vcpuCount = vcpuCount
        self.memoryInGb = memoryInGb
        self.cloudType = cloudType
        self.imageName = imageName
        self.desiredStatus = desiredStatus

    def __str__(self):
        return f"{self.podId} - {self.gpuDisplayName} - ${self.cost:0.2f}/hr - {self.cloudType.value}:{'SPOT' if self.spot else 'ON-DEMAND'}:{self.desiredStatus.value}"

    async def stop_instance(self, runpod: "RunPod", logger: loguru.Logger) -> bool:
        """Stops the instance"""
        await runpod.stop_instance(self.podId, logger)

    async def destroy_instance(self, runpod: "RunPod", logger: loguru.Logger) -> bool:
        """Destroys the instance"""
        await runpod.destroy_instance(self.podId, logger)

    async def start_instance(
        self, runpod: "RunPod", logger: loguru.Logger, max_bid: Optional[float] = None
    ) -> bool:
        """Starts the instance"""
        await runpod.start_instance(
            self.podId, self.gpuCount, logger, max_bid, self.spot
        )


class RunPod:
    """RunPod class"""

    gql_transport: AIOHTTPTransport = None

    def __init__(self, gql_transport: AIOHTTPTransport):
        self.gql_transport = gql_transport

    async def get_on_demand_price(self, gpuTypeId: GPUTypeId, logger: loguru.Logger, gpuCount: int = 1) -> Optional[float]:
        """
        Gets the current on-demand price for the gpuTypeId

        :param gpuTypeId: the gpu type id to check
        :param logger: the logger to use
        :param gpuCount: the number of gpus to check (defaults to 1)
        :return: the current on-demand price or None if no price is available
        """
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                params = {
                    "id": gpuTypeId.value,
                    "gpuCount": gpuCount,
                }

                query = gql(
                    """query GpuTypes ($id: String!, $gpuCount: Int!) {
                            gpuTypes(input: {id: $id}) {
                                secureCloud
                                lowestPrice(input: {gpuCount: $gpuCount}) {
                                    uninterruptablePrice
                                }
                            }
                    }"""
                )

                data = await session.execute(query, variable_values=params)
                type_data: Dict[str, str] = data["gpuTypes"][0]

                if type_data["secureCloud"] and type_data["lowestPrice"]["uninterruptablePrice"] is not None:
                    return float(type_data["lowestPrice"]["uninterruptablePrice"])

                return None

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            return None

    async def get_current_bid(self, gpuTypeId: GPUTypeId, logger: loguru.Logger, gpuCount: int = 1) -> Optional[float]:
        """
        Gets the current spot price for the gpuTypeId

        :param gpuTypeId: thhe gpu type id to check
        :param logger: the logger to use
        :param gpuCount: the number of gpus to check (defaults to 1)
        :return: the current bid or None if no bid is available
        """
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                params = {
                    "id": gpuTypeId.value,
                    "gpuCount": gpuCount,
                }

                query = gql(
                    """query GpuTypes ($id: String!, $gpuCount: Int!) {
                            gpuTypes(input: {id: $id}) {
                                communityCloud
                                lowestPrice(input: {gpuCount: $gpuCount}) {
                                    minimumBidPrice
                                }
                            }
                    }"""
                )

                data = await session.execute(query, variable_values=params)
                type_data: Dict[str, str] = data["gpuTypes"][0]

                if type_data["communityCloud"] and type_data["lowestPrice"]["minimumBidPrice"] is not None:
                    return float(type_data["lowestPrice"]["minimumBidPrice"])

                return None

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            return None

    async def get_gpu_types(self, logger: loguru.Logger) -> List[Tuple[GPUTypeId, Optional[int], bool, bool, Optional[float], Optional[float]]]:
        """
        Gets the gpu types and their attributes

        :param logger: the logger to use
        :return: a list of tuples containing the gpu_type_id, memoryInGb, secureCloud, communityCloud, minimum bid price, on-demand price
        """
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                query = gql(
                    """query GpuTypes {
                        gpuTypes {
                            id
                            memoryInGb
                            secureCloud
                            communityCloud
                            lowestPrice(input: {gpuCount: 1}) {
                                minimumBidPrice
                                uninterruptablePrice
                            }
                        }
                    }"""
                )

                data = await session.execute(query)
                types_data: List[Dict[str, Any]] = data["gpuTypes"]

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            return []

        gpu_types: List[Tuple[GPUTypeId, Optional[int], bool, bool, Optional[float], Optional[float]]] = []
        for gpuInfo in types_data:
            try:
                gpu_types.append(
                    (
                        GPUTypeId(gpuInfo["id"]),
                        gpuInfo["memoryInGb"],
                        gpuInfo["secureCloud"],
                        gpuInfo["communityCloud"],
                        gpuInfo["lowestPrice"]["minimumBidPrice"],
                        gpuInfo["lowestPrice"]["uninterruptablePrice"],
                    )
                )
            except KeyError:
                logger.exception(f"Error parsing GPU type: {gpuInfo}")
                continue



        return gpu_types

    async def __create_spot_instance(
        self,
        max_bid: float,
        podName: str,
        imageName: str,
        containerDiskSize: int,
        volumeSize: int,
        volumePath: str,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        args: str,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
    ) -> RunPodInstance:
        """Creates a new spot instance using the API"""

        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                params = {
                    "podName": podName,
                    "imageName": imageName,
                    "containerDiskSize": containerDiskSize,
                    "volumeSize": volumeSize,
                    "volumePath": volumePath,
                    "gpuCount": gpuCount,
                    "gpuTypeId": gpuTypeId.value,
                    "args": args,
                    "max_bid": max_bid,
                    "minVcpuCount": minVcpuCount,
                    "minMemoryInGb": minMemoryInGb,
                    "cloudType": cloudType.value,
                }

                query = gql(
                    """mutation {{
                                podRentInterruptable(
                                    input: {{
                                        bidPerGpu: {max_bid},
                                        cloudType: {cloudType},
                                        gpuCount: {gpuCount},
                                        volumeInGb: {volumeSize},
                                        containerDiskInGb: {containerDiskSize},
                                        minVcpuCount: {minVcpuCount},
                                        minMemoryInGb: {minMemoryInGb},
                                        gpuTypeId: "{gpuTypeId}",
                                        name: "{podName}",
                                        
                                        dockerArgs: {args},
                                        volumeMountPath: "{volumePath}",
                                        imageName: "{imageName}",

                                        templateId: "{templateId}",
                                    }}
                                ) {{
                                    id
                                    imageName
                                    podType
                                    machineId
                                    costPerHr
                                    gpuCount
                                    vcpuCount
                                    memoryInGb
                                    desiredStatus
                                    machine {{
                                        podHostId
                                        gpuDisplayName
                                    }}
                                }}
                            }}""".format(
                        **params
                    )
                )

                data = await session.execute(query)
                pod_data: Dict[str, str] = data["podRentInterruptable"]

                pod: RunPodInstance = RunPodInstance(
                    podName=params["podName"],
                    cost=float(pod_data["costPerHr"]),
                    podId=pod_data["id"],
                    podHostId=pod_data["machine"]["podHostId"],
                    spot=pod_data["podType"] == "INTERRUPTABLE",
                    gpuDisplayName=gpuTypeId,
                    gpuCount=int(pod_data["gpuCount"]),
                    vcpuCount=int(pod_data["vcpuCount"]),
                    memoryInGb=int(pod_data["memoryInGb"]),
                    cloudType=cloudType,
                    imageName=imageName,
                    desiredStatus=PodStatus[pod_data["desiredStatus"]],
                )

                return pod

        except (TransportServerError, TransportQueryError) as e:
            if "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
            return None

    async def __create_spot_instance_from_template_id(
        self,
        max_bid: float,
        podName: str,
        templateId: str,
        containerDiskSize: int,
        volumeSize: int,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
    ) -> RunPodInstance:
        """Creates a new spot instance using the API"""

        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                params = {
                    "podName": podName,
                    "templateId": templateId,
                    "containerDiskSize": containerDiskSize,
                    "volumeSize": volumeSize,
                    "gpuCount": gpuCount,
                    "gpuTypeId": str(gpuTypeId),
                    "minVcpuCount": minVcpuCount,
                    "minMemoryInGb": minMemoryInGb,
                    "max_bid": max_bid,
                    "cloudType": str(cloudType)
                }

                query = gql(
                    """mutation {{
                                podRentInterruptable(
                                    input: {{
                                        bidPerGpu: {max_bid},
                                        cloudType: {cloudType},
                                        gpuCount: {gpuCount},
                                        volumeInGb: {volumeSize},
                                        containerDiskInGb: {containerDiskSize},
                                        minVcpuCount: {minVcpuCount},
                                        minMemoryInGb: {minMemoryInGb},
                                        gpuTypeId: "{gpuTypeId}",
                                        name: "{podName}",
                                        templateId: "{templateId}",
                                    }}
                                ) {{
                                    id
                                    imageName
                                    podType
                                    machineId
                                    costPerHr
                                    gpuCount
                                    vcpuCount
                                    memoryInGb
                                    imageName
                                    desiredStatus
                                    machine {{
                                        podHostId
                                        gpuDisplayName
                                    }}
                                }}
                            }}""".format(
                        **params
                    )
                )

                data = await session.execute(query)
                pod_data: Dict[str, str] = data["podRentInterruptable"]

                pod: RunPodInstance = RunPodInstance(
                    podName=params["podName"],
                    cost=float(pod_data["costPerHr"]),
                    podId=pod_data["id"],
                    podHostId=pod_data["machine"]["podHostId"],
                    spot=pod_data["podType"] == "INTERRUPTABLE",
                    gpuDisplayName=gpuTypeId,
                    gpuCount=int(pod_data["gpuCount"]),
                    vcpuCount=int(pod_data["vcpuCount"]),
                    memoryInGb=int(pod_data["memoryInGb"]),
                    cloudType=cloudType,
                    imageName=pod_data["imageName"],
                    desiredStatus=PodStatus[pod_data["desiredStatus"]],
                )

                return pod

        except (TransportServerError, TransportQueryError) as e:
            if "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
            return None

    async def __create_on_demand_instance(
        self,
        podName: str,
        imageName: str,
        containerDiskSize: int,
        volumeSize: int,
        volumePath: str,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        args: str,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
    ) -> RunPodInstance:
        """Creates a new spot instance using the API"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                # make post request with bearer token
                params = {
                    "podName": podName,
                    "imageName": imageName,
                    "containerDiskSize": containerDiskSize,
                    "volumeSize": volumeSize,
                    "volumePath": volumePath,
                    "gpuCount": gpuCount,
                    "gpuTypeId": gpuTypeId.value,
                    "args": args,
                    "minVcpuCount": minVcpuCount,
                    "minMemoryInGb": minMemoryInGb,
                    "cloudType": cloudType.value,
                }

                query = gql(
                    """mutation {{
                                podFindAndDeployOnDemand(
                                    input: {{
                                        cloudType: {cloudType},
                                        gpuCount: {gpuCount},
                                        volumeInGb: {volumeSize},
                                        containerDiskInGb: {containerDiskSize},
                                        minVcpuCount: {minVcpuCount},
                                        minMemoryInGb: {minMemoryInGb},
                                        gpuTypeId: "{gpuTypeId}",
                                        name: "{podName}",
                                        imageName: "{imageName}",
                                        dockerArgs: {args},
                                        volumeMountPath: "{volumePath}",
                                    }}
                                ) {{
                                    id
                                    imageName
                                    podType
                                    machineId
                                    costPerHr
                                    gpuCount
                                    vcpuCount
                                    memoryInGb
                                    desiredStatus
                                    machine {{
                                        podHostId
                                        gpuDisplayName
                                    }}
                                }}
                            }}""".format(
                        **params
                    )
                )

                data = await session.execute(query)
                print(data)
                pod_data: Dict[str, str] = data["podRentInterruptable"]

                pod: RunPodInstance = RunPodInstance(
                    podName=params["podName"],
                    cost=float(pod_data["costPerHr"]),
                    podId=pod_data["id"],
                    podHostId=pod_data["machine"]["podHostId"],
                    spot=pod_data["podType"] == "INTERRUPTABLE",
                    gpuDisplayName=gpuTypeId,
                    gpuCount=int(pod_data["gpuCount"]),
                    vcpuCount=int(pod_data["vcpuCount"]),
                    memoryInGb=int(pod_data["memoryInGb"]),
                    cloudType=cloudType,
                    imageName=imageName,
                    desiredStatus=PodStatus[pod_data["desiredStatus"]]
                )

                return pod

        except (TransportServerError, TransportQueryError) as e:
            if "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
            return None

    async def __create_on_demand_instance_from_template_id(
        self,
        podName: str,
        templateId: str,
        containerDiskSize: int,
        volumeSize: int,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
    ) -> RunPodInstance:
        """Creates a new spot instance using the API"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                # make post request with bearer token
                params = {
                    "podName": podName,
                    "templateId": templateId,
                    "containerDiskSize": containerDiskSize,
                    "volumeSize": volumeSize,
                    "gpuCount": gpuCount,
                    "gpuTypeId": gpuTypeId.value,
                    "minVcpuCount": minVcpuCount,
                    "minMemoryInGb": minMemoryInGb,
                    "cloudType": cloudType.value,
                }

                query = gql(
                    """mutation {{
                                podFindAndDeployOnDemand(
                                    input: {{
                                        cloudType: {cloudType},
                                        gpuCount: {gpuCount},
                                        volumeInGb: {volumeSize},
                                        containerDiskInGb: {containerDiskSize},
                                        minVcpuCount: {minVcpuCount},
                                        minMemoryInGb: {minMemoryInGb},
                                        gpuTypeId: "{gpuTypeId}",
                                        name: "{podName}",
                                        templateId: "{templateId}",
                                    }}
                                ) {{
                                    id
                                    imageName
                                    podType
                                    machineId
                                    costPerHr
                                    gpuCount
                                    vcpuCount
                                    memoryInGb
                                    imageName
                                    desiredStatus
                                    machine {{
                                        podHostId
                                        gpuDisplayName
                                    }}
                                }}
                            }}""".format(
                        **params
                    )
                )

                data = await session.execute(query)
                print(data)
                pod_data: Dict[str, str] = data["podRentInterruptable"]

                pod: RunPodInstance = RunPodInstance(
                    podName=params["podName"],
                    cost=float(pod_data["costPerHr"]),
                    podId=pod_data["id"],
                    podHostId=pod_data["machine"]["podHostId"],
                    spot=pod_data["podType"] == "INTERRUPTABLE",
                    gpuDisplayName=gpuTypeId,
                    gpuCount=int(pod_data["gpuCount"]),
                    vcpuCount=int(pod_data["vcpuCount"]),
                    memoryInGb=int(pod_data["memoryInGb"]),
                    cloudType=cloudType,
                    imageName=pod_data["imageName"],
                    desiredStatus=PodStatus[pod_data["desiredStatus"]],
                )

                return pod

        except (TransportServerError, TransportQueryError) as e:
            if "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
            return None

    async def create_instance(
        self,
        max_bid: float,
        podName: str,
        imageName: str,
        containerDiskSize: int,
        volumeSize: int,
        volumePath: str,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        args: str,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
        spot: bool = True,
    ) -> RunPodInstance:
        """Creates a new instance"""
        pod: RunPodInstance = None
        args = json.dumps(args)
        if spot:
            pod = await self.__create_spot_instance(
                max_bid,
                podName,
                imageName,
                containerDiskSize,
                volumeSize,
                volumePath,
                gpuCount,
                gpuTypeId,
                minVcpuCount,
                minMemoryInGb,
                args,
                logger,
                cloudType,
            )
        else:
            pod = await self.__create_on_demand_instance(
                podName,
                imageName,
                containerDiskSize,
                volumeSize,
                volumePath,
                gpuCount,
                gpuTypeId,
                minVcpuCount,
                minMemoryInGb,
                args,
                logger,
                cloudType,
            )

        if pod is None:
            return None

        podId = pod.podId

        pod_ = await self.get_pod_by_id(podId, logger)
        while pod_ is None:
            await asyncio.sleep(3)  # wait for pod to finish start
            pod_ = await self.get_pod_by_id(podId, logger)

        return pod

    async def create_instance_from_template_id(
        self,
        max_bid: float,
        podName: str,
        templateId: str,
        containerDiskSize: int,
        volumeSize: int,
        gpuCount: int,
        gpuTypeId: GPUTypeId,
        minVcpuCount: int,
        minMemoryInGb: int,
        logger: loguru.Logger,
        cloudType: CloudType = CloudType.COMMUNITY,
        spot: bool = True,
    ) -> RunPodInstance:
        """Creates a new instance"""
        pod: RunPodInstance = None
        if spot:
            pod = await self.__create_spot_instance_from_template_id(
                max_bid,
                podName,
                templateId,
                containerDiskSize,
                volumeSize,
                gpuCount,
                gpuTypeId,
                minVcpuCount,
                minMemoryInGb,
                logger,
                cloudType,
            )
        else:
            pod = await self.__create_on_demand_instance_from_template_id(
                podName,
                templateId,
                containerDiskSize,
                volumeSize,
                gpuCount,
                gpuTypeId,
                minVcpuCount,
                minMemoryInGb,
                logger,
                cloudType,
            )

        if pod is None:
            return None

        podId = pod.podId

        pod_ = await self.get_pod_by_id(podId, logger)
        while pod_ is None:
            await asyncio.sleep(3)  # wait for pod to finish start
            pod_ = await self.get_pod_by_id(podId, logger)

        return pod

    async def get_pod_by_id(
        self, podId: str, logger: loguru.Logger
    ) -> Optional[RunPodInstance]:
        """Gets a pod from the API by its podId"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:

                params = {
                    "podId": podId,
                }

                query = gql(
                    """query myPods($podId: String!) {
                            pod (input: {podId: $podId}) {
                                id
                                podType
                                costPerHr
                                name
                                gpuCount
                                vcpuCount
                                memoryInGb
                                imageName
                                desiredStatus
                                machine {
                                    podHostId
                                    gpuDisplayName
                                    secureCloud
                                }
                            }
                            
                    }"""
                )

                data = await session.execute(query, params)

                pod_data: Dict[str, str] = data["pod"]

                podName = pod_data["name"]
                podId = pod_data["id"]
                podHostId = pod_data["machine"]["podHostId"]
                cost = float(pod_data["costPerHr"]) if "costPerHr" in pod_data else None
                # Not a typo, enum has a spelling issue in API
                spot = pod_data["podType"] == "INTERRUPTABLE"
                try:
                    gpuDisplayName = GPUTypeId.from_gpuDisplayName(
                        pod_data["machine"]["gpuDisplayName"]
                    )
                except ValueError:
                    gpuDisplayName = None
                gpuCount = int(pod_data["gpuCount"])
                vcpuCount = int(pod_data["vcpuCount"])
                memoryInGb = int(pod_data["memoryInGb"])
                imageName = pod_data["imageName"]
                secureCloud: bool = pod_data["machine"]["secureCloud"]

                pod = RunPodInstance(
                    podName=podName,
                    cost=cost,
                    podId=podId,
                    podHostId=podHostId,
                    spot=spot,
                    gpuDisplayName=gpuDisplayName,
                    gpuCount=gpuCount,
                    vcpuCount=vcpuCount,
                    memoryInGb=memoryInGb,
                    imageName=imageName,
                    cloudType=CloudType.SECURE if secureCloud else CloudType.COMMUNITY,
                    desiredStatus=PodStatus[pod_data["desiredStatus"]]
                )

                return pod
        except TransportQueryError as e:
            if (
                len(e.errors) >= 1
                and e.errors[0]["extensions"]["code"] == "INTERNAL_SERVER_ERROR"
            ):
                # podId not found
                return None
            else:
                logger.exception(e)
                logger.exception(query)
                raise RunPodException(f"Failed to get pod {podId} with error: {e}")

        except TransportServerError as e:
            logger.exception(e)
            logger.exception(query)
            raise RunPodException(f"Failed to get pod {podId} with error: {e}")

    async def get_pods(self, logger: loguru.Logger) -> List[RunPodInstance]:
        """Gets all the pods from the API"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                query = gql(
                    """query myPods {
                            myself {
                                pods {
                                    id
                                    name
                                    podType
                                    gpuCount
                                    vcpuCount
                                    memoryInGb
                                    imageName
                                    costPerHr
                                    desiredStatus
                                    machine {
                                        podHostId
                                        gpuDisplayName
                                        secureCloud
                                    }
                                }
                            }
                    }"""
                )

                data = await session.execute(query)
                pods_data: List[Dict[str, str]] = data["myself"]["pods"]
                pods: List[RunPodInstance] = []

                for pod_data in pods_data:
                    podName = pod_data["name"]
                    podId = pod_data["id"]
                    podHostId = pod_data["machine"]["podHostId"]
                    cost = (
                        float(pod_data["costPerHr"])
                        if "costPerHr" in pod_data
                        else None
                    )
                    # Not a typo, enum has a spelling issue in API
                    spot = pod_data["podType"] == "INTERRUPTABLE"
                    try:
                        gpuDisplayName = GPUTypeId.from_gpuDisplayName(
                            pod_data["machine"]["gpuDisplayName"]
                        )
                    except ValueError:
                        gpuDisplayName = None
                    gpuCount = int(pod_data["gpuCount"])
                    vcpuCount = int(pod_data["vcpuCount"])
                    memoryInGb = int(pod_data["memoryInGb"])
                    imageName = pod_data["imageName"]
                    secureCloud: bool = pod_data["machine"]["secureCloud"]

                    pod = RunPodInstance(
                        podName=podName,
                        cost=cost,
                        podId=podId,
                        podHostId=podHostId,
                        spot=spot,
                        gpuDisplayName=gpuDisplayName,
                        gpuCount=gpuCount,
                        vcpuCount=vcpuCount,
                        memoryInGb=memoryInGb,
                        imageName=imageName,
                        cloudType=CloudType.SECURE if secureCloud else CloudType.COMMUNITY,
                        desiredStatus=PodStatus[pod_data["desiredStatus"]],
                    )
                    pods.append(pod)

                return pods

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            raise RunPodException(f"Failed to get pods with error: {e}")

    async def test_connection(self, logger: loguru.Logger) -> bool:
        """Tests the connection to the runpod api"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:
                # make post request with bearer token
                query = gql(
                    """query myPods {
                            myself {
                                id
                            }
                    }"""
                )

                result = await session.execute(query)
                if result is None:
                    return False

                # Authentication is successful if we are not guest
                return result["myself"]["id"] != "guest"

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            return False

    async def stop_instance(self, podId: str, logger: loguru.Logger) -> bool:
        """Stops an instance by the podId"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:

                params = {
                    "podId": podId,
                }

                query = gql(
                    """mutation($podId: String!) {
                        podStop(input: {podId: $podId}) {
                            id
                            desiredStatus
                        }
                    }"""
                )

                data = await session.execute(query, params)

                return (
                    data["podStop"]["id"] == podId
                    and data["podStop"]["desiredStatus"] == "EXITED"
                )

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            logger.exception(query)
            return False

    async def destroy_instance(self, podId: str, logger: loguru.Logger) -> bool:
        """Destroys the instance by the podId"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:

                params = {
                    "input": {
                        "podId": podId,
                    }
                }

                query = gql(
                    """mutation terminatePod($input: PodTerminateInput!) {
                        podTerminate(input: $input)
                    }"""
                )

                data = await session.execute(query, params)

                return data["podTerminate"] is None

        except (TransportServerError, TransportQueryError) as e:
            logger.exception(e)
            logger.exception(query)
            return False

    async def __start_spot_instance(
        self, podId: str, gpuCount: int, max_bid: float, logger: loguru.Logger
    ) -> bool:
        """Starts a spot instance by the podId with a gpuCount and a max_bid per GPU"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:

                params = {
                    "podId": podId,
                    "maxBid": max_bid,
                    "gpuCount": gpuCount,
                }

                query = gql(
                    """mutation($podId: String!, $maxBid: Float!) {
                        podBidResume(input: {podId: $podId, bidPerGpu: $maxBid, gpuCount: 1}) {
                            id
                            desiredStatus
                            imageName
                            env
                            machineId
                            machine {
                            podHostId
                            }
                        }
                    }"""
                )

                data = await session.execute(query, params)
                pod_data: Dict[str, str] = data["podBidResume"]

                return (
                    pod_data["id"] == podId and pod_data["desiredStatus"] == "RUNNING"
                )
        except TransportQueryError as e:
            if (
                len(e.errors) >= 1
                and "Cannot resume a pod that is not in exited state"
                in e.errors[0]["message"]
            ):
                logger.info(f"Pod {podId} is already running")
                return True
            elif "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
                logger.exception(query)
                return False

        except TransportServerError as e:
            logger.exception(e)
            logger.exception(query)
            return False

    async def __start_on_demand_instance(
        self, podId: str, gpuCount: int, logger: loguru.Logger
    ) -> bool:
        """Starts an on-demand instance by the podId with a gpuCount"""
        try:
            async with Client(
                transport=self.gql_transport,
                fetch_schema_from_transport=False,
            ) as session:

                params = {
                    "podId": podId,
                    "gpuCount": gpuCount,
                }

                query = gql(
                    """mutation($podId: String!, $maxBid: Float!) {
                        podResume(input: {podId: $podId, gpuCount: 1}) {
                            id
                            desiredStatus
                            imageName
                            env
                            machineId
                            machine {
                            podHostId
                            }
                        }
                    }"""
                )

                data = await session.execute(query, params)
                pod_data: Dict[str, str] = data["podResume"]

                return (
                    pod_data["id"] == podId and pod_data["desiredStatus"] == "RUNNING"
                )
        except TransportQueryError as e:
            if (
                len(e.errors) >= 1
                and "Cannot resume a pod that is not in exited state"
                in e.errors[0]["message"]
            ):
                logger.info(f"Pod {podId} is already running")
                return True
            elif "outbid" in e.errors[0]["message"]:
                raise OutbidException(e.errors[0]["message"])
            else:
                logger.exception(e)
                logger.exception(query)
                return False

        except TransportServerError as e:
            logger.exception(e)
            logger.exception(query)
            return False

    async def start_instance(
        self,
        podId: str,
        gpuCount: int,
        logger: loguru.Logger,
        max_bid: Optional[float] = None,
        spot: bool = False,
    ):
        """Starts an instance by the podId"""
        if spot:
            return await self.__start_spot_instance(podId, gpuCount, max_bid, logger)
        else:
            return await self.__start_on_demand_instance(podId, gpuCount, logger)
