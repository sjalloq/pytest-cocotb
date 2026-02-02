import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def counter_basic(dut):
    """Check that the counter increments after reset."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Wait a few cycles and check count increments
    await RisingEdge(dut.clk)
    prev = int(dut.count.value)
    await RisingEdge(dut.clk)
    curr = int(dut.count.value)
    assert curr == prev + 1, f"Expected {prev + 1}, got {curr}"
