import numpy as np
from apytypes import APyFixed, APyFixedArray
from apytypes import QuantizationMode
from apytypes import OverflowMode

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from cocotb_tools.runner import get_runner

import pytest

import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)


class ProcessorNode:
    def __init__(self, dut):
        self.dut = dut
        self.rng = np.random.default_rng()

    def data_in_ports(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [self.dut.noinput,]

    def data_in_int_bits(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_in_frac_bits(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_out_ports(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [self.dut.nooutput,]

    def data_out_int_bits(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_out_frac_bits(self):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def random_fixed_array(self, length, int_bits, frac_bits):
        bits = int_bits + frac_bits
        MAX_VALUE = (2 ** (bits - 1) - 1) / 2 ** frac_bits
        MIN_VALUE = -(2 ** (bits - 1)) / 2 ** frac_bits
        np_data = self.rng.uniform(
            low=MIN_VALUE,
            high=MAX_VALUE,
            size=(length,)
        )
        ap_data = APyFixedArray.from_array(
            np_data,
            int_bits=int_bits,
            frac_bits=frac_bits
        )
        return ap_data

    def random_data_in_arrays(self, length):
        int_bits = self.data_in_int_bits()
        frac_bits = self.data_in_frac_bits()

        data_in = [self.random_fixed_array(length, i, f)
                   for (i, f) in zip(int_bits, frac_bits)]
        return data_in

    def expected_output_uncasted(self, data_in):
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [APyFixed(data_in, 1, 1), ]

    def expected_output(self, data_in):
        int_bits = self.data_out_int_bits()
        frac_bits = self.data_out_frac_bits()

        data_out_uncasted = self.expected_output_uncasted(data_in)

        data_out = [
            d.cast(
                int_bits=i,
                frac_bits=f,
                # we follow the sfixed library convention
                # see IEEE 1076-2008 section G.4.4
                quantization=QuantizationMode.RND_CONV,
                overflow=OverflowMode.SAT
            ) for (d, i, f) in zip(data_out_uncasted, int_bits, frac_bits)
        ]

        for du, dc, port in zip(
            data_out_uncasted,
            data_out,
            self.data_out_ports()
        ):
            res = float(du - dc)
            fu = float(du)
            if abs(res) > 0.01 * abs(fu) and fu != 0:
                pn = port._name
                logger.warning(
                    f"Truncation difference exceeded 1% for out port {pn}."
                )
        return data_out

    async def test_processor_node(self, N):
        # generate random input data
        data_in = self.random_data_in_arrays(N+3)

        # initialize the inputs
        for port_in in self.data_in_ports():
            port_in.value = 0

        # reset the node
        self.dut.rst.value = 1

        # initialize the clock and enable computation
        clk = Clock(self.dut.clk, 10, units="ns")
        clk.start()

        # remove the reset
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 0

        for n, d_n in enumerate(zip(*data_in)):
            await RisingEdge(self.dut.clk)

            # set data in
            for d, p in zip(d_n, self.data_in_ports()):
                p.value = d.to_bits()

            # we have 3 clk cycle latency for the output because:
            # at +1clk the input is set
            # at +2clk the values are in the node
            # ar +3clk the out are out (2clk latency)
            if n < 3:
                continue

            expect_out = self.expected_output([d[n - 3] for d in data_in])

            for e, o in zip(expect_out, self.data_out_ports()):
                assert o.value.to_unsigned() == e.to_bits()

        clk.stop()


class ProcessorNodeA(ProcessorNode):
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
            self.dut.data_out_se,
            self.dut.data_out_sw,
            self.dut.data_out_n
        ]

    def data_out_int_bits(self):
        return [
            self.dut.SE_INTEGER_WIDTH.value,
            self.dut.SW_INTEGER_WIDTH.value,
            self.dut.N_INTEGER_WIDTH.value,
        ]

    def data_out_frac_bits(self):
        return [
            self.dut.SE_DECIMAL_WIDTH.value,
            self.dut.SW_DECIMAL_WIDTH.value,
            self.dut.N_DECIMAL_WIDTH.value,
        ]

    def expected_output_uncasted(self, data_in):
        a, b, c = data_in
        return [a, b, c + a * b]


@cocotb.test()
async def a_processor_node_a(dut):
    t = ProcessorNodeA(dut)
    await t.test_processor_node(100)


input_int = [2 ** i for i in range(2, 6)]
input_frac = [2 ** i for i in range(2, 6)]
output_int = [i for i in range(2, 4)]
output_frac = [i for i in range(2, 4)]


@pytest.mark.parametrize("in_i", input_int)
@pytest.mark.parametrize("in_f", input_frac)
@pytest.mark.parametrize("out_s_i", output_int)
@pytest.mark.parametrize("out_s_f", output_frac)
def test_runner(in_i, in_f, out_s_i, out_s_f):

    sim = os.getenv("SIM", "nvc")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "src" / "processor_node_a.vhd"]

    out_i = in_i * out_s_i
    out_f = in_f * out_s_f
    generics = {
        "NW_INTEGER_WIDTH": in_i,
        "NW_DECIMAL_WIDTH": in_f,
        "NE_INTEGER_WIDTH": in_i,
        "NE_DECIMAL_WIDTH": in_f,
        "S_INTEGER_WIDTH": in_i,
        "S_DECIMAL_WIDTH": in_f,
        "SE_INTEGER_WIDTH": out_i,
        "SE_DECIMAL_WIDTH": out_f,
        "SW_INTEGER_WIDTH": out_i,
        "SW_DECIMAL_WIDTH": out_f,
        "N_INTEGER_WIDTH": out_i,
        "N_DECIMAL_WIDTH": out_f
    }

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="processor_node_a",
        always=True,
        build_dir="sim_build/processor_node_a",
        parameters=generics
    )

    runner.test(
        hdl_toplevel="processor_node_a",
        test_module="test_processor_node_a",
        plusargs=[f"--wave=in_{in_i}_{in_f}_out_{out_i}_{out_f}.fst"],
    )


if __name__ == "__main__":
    test_runner(8, 8, 2, 2)
