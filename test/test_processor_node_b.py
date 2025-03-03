
"""
------------------------------
------------------------------
--- Cholesky factorization ---
---        using           ---
--- systolic architecture  ---
------------------------------
------------------------------
--- Marco Riggirello, 2025 ---
------------------------------
------------------------------
"""

import os
from pathlib import Path
import logging

import pytest


import cocotb
from cocotb_tools.runner import get_runner

from test_processor_node import ProcessorNode

logger = logging.getLogger(__name__)


class ProcessorNodeB(ProcessorNode):
    """
        Tests the processor nodes of type b)
        as shown in fig 4 of reference article.
    """

    def data_in_ports(self):
        return [
            self.dut.data_in_nw,
            self.dut.data_in_ne,
            self.dut.data_in_s
        ]

    def data_in_int_bits(self):
        return [
            self.dut.NW_INTEGER_WIDTH.value,
            self.dut.NE_INTEGER_WIDTH.value,
            self.dut.S_INTEGER_WIDTH.value,
        ]

    def data_in_frac_bits(self):
        return [
            self.dut.NW_DECIMAL_WIDTH.value,
            self.dut.NE_DECIMAL_WIDTH.value,
            self.dut.S_DECIMAL_WIDTH.value,
        ]

    def data_out_ports(self):
        return [
            self.dut.data_out_sw,
            self.dut.data_out_n
        ]

    def data_out_int_bits(self):
        return [
            self.dut.SW_INTEGER_WIDTH.value,
            self.dut.N_INTEGER_WIDTH.value,
        ]

    def data_out_frac_bits(self):
        return [
            self.dut.SW_DECIMAL_WIDTH.value,
            self.dut.N_DECIMAL_WIDTH.value,
        ]

    def expected_output_uncasted(self, data_in):
        a, b, c = data_in
        return [-(a * b), c - a ** 2 * b]


@cocotb.test()
async def b_processor_node_b(dut):
    """
        Make the cocotb test with 100 events.
    """
    t = ProcessorNodeB(dut)
    await t.test_processor_node(100)


input_int = [2 ** i for i in range(2, 6)]
input_frac = [2 ** i for i in range(2, 6)]
output_int = range(2, 4)
output_frac = range(2, 4)


@pytest.mark.parametrize("in_i", input_int)
@pytest.mark.parametrize("in_f", input_frac)
@pytest.mark.parametrize("out_s_i", output_int)
@pytest.mark.parametrize("out_s_f", output_frac)
def test_runner(in_i, in_f, out_s_i, out_s_f):
    """
        cocotb runner for different input/output sizes.
    """

    sim = os.getenv("SIM", "nvc")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "src" / "processor_node_b.vhd"]

    out_i = in_i * out_s_i
    out_f = in_f * out_s_f
    generics = {
        "NW_INTEGER_WIDTH": in_i,
        "NW_DECIMAL_WIDTH": in_f,
        "NE_INTEGER_WIDTH": in_i,
        "NE_DECIMAL_WIDTH": in_f,
        "S_INTEGER_WIDTH": in_i,
        "S_DECIMAL_WIDTH": in_f,
        "SW_INTEGER_WIDTH": out_i,
        "SW_DECIMAL_WIDTH": out_f,
        "N_INTEGER_WIDTH": out_i,
        "N_DECIMAL_WIDTH": out_f
    }

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="processor_node_b",
        always=True,
        build_dir="sim_build/processor_node_b",
        parameters=generics
    )

    runner.test(
        hdl_toplevel="processor_node_b",
        test_module="test_processor_node_b",
        plusargs=[f"--wave=in_{in_i}_{in_f}_out_{out_i}_{out_f}.fst"],
    )


if __name__ == "__main__":
    test_runner(8, 8, 2, 2)
