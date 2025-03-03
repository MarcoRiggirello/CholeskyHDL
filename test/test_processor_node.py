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

import logging


import numpy as np

from apytypes import APyFixed, APyFixedArray
from apytypes import QuantizationMode
from apytypes import OverflowMode

from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


logger = logging.getLogger(__name__)


class ProcessorNode:
    """
        Base class to implement test of the processor
        nodes of the systolic array architecture.
    """

    def __init__(self, dut):
        self.dut = dut
        self.rng = np.random.default_rng()

    def data_in_ports(self):
        """
            Returns a list of handlers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [self.dut.noinput,]

    def data_in_int_bits(self):
        """
            Returns a list of integers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_in_frac_bits(self):
        """
            Returns a list of integers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_out_ports(self):
        """
            Returns a list of handlers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [self.dut.nooutput,]

    def data_out_int_bits(self):
        """
            Returns a list of integers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def data_out_frac_bits(self):
        """
            Returns a list of integers. Must be specialized in child classes.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [None,]

    def random_fixed_array(self, length, int_bits, frac_bits):
        """
            Generate a random fixed point number.
        """
        bits = int_bits + frac_bits
        max_value = (2 ** (bits - 1) - 1) / 2 ** frac_bits
        min_value = -(2 ** (bits - 1)) / 2 ** frac_bits
        np_data = self.rng.uniform(
            low=min_value,
            high=max_value,
            size=(length,)
        )
        ap_data = APyFixedArray.from_array(
            np_data,
            int_bits=int_bits,
            frac_bits=frac_bits
        )
        return ap_data

    def random_data_in_arrays(self, length):
        """
            Generate a list of array of data for each in port.
        """
        int_bits = self.data_in_int_bits()
        frac_bits = self.data_in_frac_bits()

        data_in = [self.random_fixed_array(length, i, f)
                   for (i, f) in zip(int_bits, frac_bits)]
        return data_in

    def expected_output_uncasted(self, data_in):
        """
            The expected out value with full precision.
            Must be specialized in child class.
        """
        logger.error(
            "The method is not overloaded by child class, test cannot work."
        )
        return [APyFixed(data_in, 1, 1), ]

    def expected_output(self, data_in):
        """
            The expected output with the given out precision.
        """
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
                pn = port._name  # pylint: disable=protected-access
                logger.warning(
                    "Truncation difference exceeded 1%% for out port %s.", pn
                )
        return data_out

    async def test_processor_node(self, n_events):
        """
            Test loop.
        """
        # generate random input data
        data_in = self.random_data_in_arrays(n_events+3)

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
