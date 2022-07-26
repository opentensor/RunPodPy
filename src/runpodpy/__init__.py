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

__version__ = "0.3.3"

from enum import Enum


class CloudType(Enum):
    COMMUNITY = "COMMUNITY"
    SECURE = "SECURE"

    def __str__(self):
        return self.value


class GPUTypeId(Enum):
    RTX_A4000 = "NVIDIA RTX A4000"
    RTX_A4500 = "NVIDIA RTX A4500"
    RTX_A5000 = "NVIDIA RTX A5000"
    RTX_A6000 = "NVIDIA RTX A6000"
    A100_80GB = "NVIDIA A100 80GB PCIe"
    A40 = "NVIDIA A40"
    RTX_3070 = "NVIDIA GeForce RTX 3070"
    RTX_3080 = "NVIDIA GeForce RTX 3080"
    RTX_3080_TI = "NVIDIA GeForce RTX 3080 Ti"
    RTX_3090 = "NVIDIA GeForce RTX 3090"
    V100_FHHL = "Tesla V100-FHHL-16GB"
    V100_SXM2 = "Tesla V100-SXM2-16GB"
    TESLA_V100 = "Tesla V100-PCIE-16GB"

    def __str__(self):
        return self.value

    @classmethod
    def from_gpuDisplayName(cls, s: str) -> "GPUTypeId":
        s_ = s.replace(" ", "_").upper()
        typeId = getattr(GPUTypeId, s_, None)
        if typeId is None:
            raise ValueError(f"Unknown GPU type: {s}")
        return typeId

class PodStatus(Enum):
    """
    Status (desired status) of a pod.
    """
    RUNNING = "RUNNING"
    EXITED = "EXITED"

    def __str__(self):
        return self.value
