# AXI Combat
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
# AXI Combat is released under the GNU General Public License v3 or above.

import multiprocessing as mp
import OpsConv
import Multi
import sys
import PIL._tkinter_finder # for freezing

if __name__ == "__main__":
    mp.freeze_support()
    mp.set_start_method("spawn")
    OpsConv.genInfo()
    Multi.run()
