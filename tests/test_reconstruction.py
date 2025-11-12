import pytest
import numpy as np
import skrf as rf
from pathlib import Path
import subprocess
import os
import sys

from smat_merge.reconstruct_nport import reconstruct_nport

def create_random_network(ports):
    freq = rf.Frequency(1, 10, 101, 'ghz')
    s = np.random.rand(len(freq), ports, ports) + 1j * np.random.rand(len(freq), ports, ports)
    ntwk = rf.Network(frequency=freq, s=s)
    return ntwk

def test_reconstruction(tmp_path):
    # Create a random 5-port network
    n_ports = 5
    original_ntwk = create_random_network(n_ports)
    
    # Define sub-networks (1-based port indexing)
    sub_ntwks_ports = {
        'meas_1234': [1, 2, 3, 4],
        'meas_1235': [1, 2, 3, 5],
        'meas_1245': [1, 2, 4, 5],
        'meas_1345': [1, 3, 4, 5],
        'meas_2345': [2, 3, 4, 5],
    }
    sub_ntwks = {}
    for name, ports in sub_ntwks_ports.items():
        # skrf.subnetwork uses 0-based indexing for ports
        sub_ntwks[name] = original_ntwk.subnetwork([p - 1 for p in ports])
        sub_ntwks[name].write_touchstone(tmp_path / f'{name}.s{len(ports)}p')

    # Test with reconstruct_nport function
    networks = [rf.Network(tmp_path / f'{name}.s{len(ports)}p') for name, ports in sub_ntwks_ports.items()]
    port_sets = list(sub_ntwks_ports.values())
    reconstructed_ntwk_func, _ = reconstruct_nport(networks, port_sets, n_ports=n_ports)

    assert np.allclose(original_ntwk.s, reconstructed_ntwk_func.s, atol=1e-6)

    # Test with command line utility
    output_filename = tmp_path / 'reconstructed_cli.s5p'
    
    configs = []
    for name, ports in sub_ntwks_ports.items():
        filepath = tmp_path / f'{name}.s{len(ports)}p'
        port_str = ",".join(map(str, ports))
        configs.append(f'{filepath}:{port_str}')

    cmd = [
        sys.executable, '-m', 'smat_merge.reconstruct_nport',
        '--n-ports', str(n_ports),
    ] + configs
    subprocess.run(cmd, check=True)

    # The CLI utility writes the output file with a default name
    cli_output_file = f'reconstructed_{n_ports}port.s{n_ports}p'
    reconstructed_ntwk_cli = rf.Network(cli_output_file)
    assert np.allclose(original_ntwk.s, reconstructed_ntwk_cli.s, atol=1e-6)

