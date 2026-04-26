#!/usr/bin/env python3
from scapy.all import Ether, IP, UDP, Raw, PcapWriter
import argparse
import struct

parser = argparse.ArgumentParser()
parser.add_argument("--packets", type=int, default=100000)
parser.add_argument("--out", default="udp_test.pcap")
parser.add_argument("--payload-bytes", type=int, default=64)
args = parser.parse_args()

writer = PcapWriter(args.out, sync=True)

for seq in range(1, args.packets + 1):
    payload = struct.pack("!Q", seq) + bytes(max(0, args.payload_bytes - 8))
    pkt = (
        Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
        / IP(src="10.0.0.1", dst="10.0.0.2")
        / UDP(sport=5000, dport=6000)
        / Raw(payload)
    )
    writer.write(pkt)

writer.close()
print(f"Wrote {args.packets} packets to {args.out}")