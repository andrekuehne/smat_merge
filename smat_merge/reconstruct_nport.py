#!/usr/bin/env python3
import argparse
import numpy as np
import skrf as rf


def reconstruct_from_networks(networks, port_sets, n_ports=5):
    """
    Reconstruct a full n_ports x n_ports S-matrix from a set of
    scikit-rf Networks measured on different port subsets.

    Parameters
    ----------
    networks : list[rf.Network]
        Measured sub-network S-parameters. Each is k-port.
    port_sets : list[tuple[int]]
        For each network, the DUT port numbers (1-based) that correspond
        to the network's ports in order. Example for a 5-port DUT:
            [(1, 2, 3, 4),
             (1, 2, 3, 5),
             (1, 2, 4, 5),
             (1, 3, 4, 5)]
    n_ports : int
        Total DUT ports (default 5).

    Returns
    -------
    full_net : rf.Network
        Reconstructed n_ports-port network.
    counts : np.ndarray
        Integer matrix (n_ports, n_ports) with number of contributions
        for each S_ij entry.
    """
    if len(networks) == 0:
        raise ValueError("No networks provided")

    # Use the first network as frequency reference
    ref_net = networks[0]
    freqs = ref_net.f  # Hz
    n_freq = len(freqs)

    # Check frequency grid consistency
    for net in networks[1:]:
        if len(net.f) != n_freq or not np.allclose(net.f, freqs):
            raise ValueError("All networks must share the same frequency grid")

    # Accumulators
    S_sum = np.zeros((n_freq, n_ports, n_ports), dtype=complex)
    counts = np.zeros((n_ports, n_ports), dtype=int)

    for net, ports in zip(networks, port_sets):
        ports = np.asarray(ports, dtype=int) - 1  # to 0-based
        k = len(ports)
        if net.nports != k:
            raise ValueError(
                f"Network '{net.name}' is {net.nports}-port but "
                f"port set has length {k}"
            )

        s = net.s  # shape (n_freq, k, k)
        for li, gi in enumerate(ports):
            for lj, gj in enumerate(ports):
                S_sum[:, gi, gj] += s[:, li, lj]
                counts[gi, gj] += 1

    # Average over all contributions; entries never measured remain 0
    counts_safe = np.where(counts == 0, 1, counts)  # avoid div-by-zero
    S_full = S_sum / counts_safe[np.newaxis, :, :]

    # Zero out entries with no measurements explicitly (optional)
    S_full[:, counts == 0] = 0.0

    # Build z0 for full network (assume 50 Ω for all ports)
    z0_full = np.full((n_freq, n_ports), 50.0)

    full_net = rf.Network(frequency=ref_net.frequency, s=S_full, z0=z0_full)
    full_net.name = f"reconstructed_{n_ports}port"

    return full_net, counts


def parse_config_args(config_args):
    """
    Parse CLI config strings of the form
        file.s4p:1,2,3,4
    into (filename, (1,2,3,4)).
    """
    configs = []
    for cfg in config_args:
        try:
            fname, ports_str = cfg.split(":")
        except ValueError:
            raise ValueError(
                f"Invalid config '{cfg}'. Use format 'file.s4p:1,2,3,4'"
            )
        ports = tuple(int(p) for p in ports_str.split(",") if p.strip())
        configs.append((fname, ports))
    return configs


def main():
    # To run this script directly for testing, you can add the project root to the path
    # This allows the script to be run as `python -m smat_merge.reconstruct_nport`
    # as well as `python smat_merge/reconstruct_nport.py`
    import sys
    import os
    if __package__ is None:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct an N-port S-matrix from multiple Touchstone "
            "measurements on different port subsets using scikit-rf."
        )
    )
    parser.add_argument(
        "--n-ports",
        type=int,
        default=5,
        help="Total number of DUT ports (default: 5)",
    )
    parser.add_argument(
        "configs",
        nargs="+",
        help=(
            "Measurement configs, each as 'file.s4p:port1,port2,...'. "
            "Example for a 5-port DUT with a 4-port VNA:\n"
            "  meas_1234.s4p:1,2,3,4  meas_1235.s4p:1,2,3,5 "
            "meas_1245.s4p:1,2,4,5  meas_1345.s4p:1,3,4,5"
        ),
    )

    args = parser.parse_args()
    configs = parse_config_args(args.configs)

    # Load networks and collect port sets
    networks = []
    port_sets = []
    for fname, ports in configs:
        net = rf.Network(fname)
        net.name = fname
        networks.append(net)
        port_sets.append(ports)

    # Reconstruct full network
    full_net, counts = reconstruct_from_networks(
        networks, port_sets, n_ports=args.n_ports
    )

    # Write Touchstone (scikit-rf chooses .sNp extension automatically)
    out_basename = full_net.name
    full_net.write_touchstone(out_basename)
    print(f"Reconstructed {args.n_ports}-port network written as '{out_basename}.s{args.n_ports}p'")
    print("Counts (number of measurements contributing to each S_ij):")
    print(counts)


if __name__ == "__main__":
    main()
