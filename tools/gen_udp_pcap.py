#!/usr/bin/env python3
import argparse
import os
import socket
import struct
import time

PCAP_MAGIC_USEC = 0xA1B2C3D4
DLT_EN10MB = 1

ETH_TYPE_IPV4 = 0x0800
IP_PROTO_UDP = 17

SRC_MAC = bytes.fromhex("020000000001")
DST_MAC = bytes.fromhex("020000000002")
SRC_IP = socket.inet_aton("10.0.0.1")
DST_IP = socket.inet_aton("10.0.0.2")
SRC_PORT = 5000
DST_PORT = 6000


def ipv4_checksum(header: bytes) -> int:
    if len(header) % 2:
        header += b"\x00"

    total = 0
    for i in range(0, len(header), 2):
        total += (header[i] << 8) + header[i + 1]
        total = (total & 0xFFFF) + (total >> 16)

    return (~total) & 0xFFFF


def build_packet(seq: int, payload_bytes: int) -> bytes:
    payload = struct.pack("!Q", seq) + bytes(max(0, payload_bytes - 8))

    udp_len = 8 + len(payload)
    ip_total_len = 20 + udp_len

    eth = DST_MAC + SRC_MAC + struct.pack("!H", ETH_TYPE_IPV4)

    ip_no_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        ip_total_len,
        seq & 0xFFFF,
        0,
        64,
        IP_PROTO_UDP,
        0,
        SRC_IP,
        DST_IP,
    )

    checksum = ipv4_checksum(ip_no_checksum)

    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        ip_total_len,
        seq & 0xFFFF,
        0,
        64,
        IP_PROTO_UDP,
        checksum,
        SRC_IP,
        DST_IP,
    )

    udp = struct.pack("!HHHH", SRC_PORT, DST_PORT, udp_len, 0)

    return eth + ip + udp + payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packets", type=int, default=100000)
    parser.add_argument("--out", default="udp_test.pcap")
    parser.add_argument("--payload-bytes", type=int, default=64)
    parser.add_argument("--log-every", type=int, default=100000)
    parser.add_argument("--flush-every", type=int, default=10000)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    global_header = struct.pack(
        "<IHHIIII",
        PCAP_MAGIC_USEC,
        2,
        4,
        0,
        0,
        65535,
        DLT_EN10MB,
    )

    start = time.time()
    print(f"Generating {args.packets:,} packets -> {args.out}")
    print(f"Payload bytes per packet: {args.payload_bytes}")

    with open(args.out, "wb") as f:
        f.write(global_header)

        buffer = bytearray()
        base_ts = int(start)

        for seq in range(1, args.packets + 1):
            pkt = build_packet(seq, args.payload_bytes)

            ts_sec = base_ts
            ts_usec = seq % 1_000_000

            rec_header = struct.pack(
                "<IIII",
                ts_sec,
                ts_usec,
                len(pkt),
                len(pkt),
            )

            buffer += rec_header
            buffer += pkt

            if seq % args.flush_every == 0:
                f.write(buffer)
                buffer.clear()

            if seq % args.log_every == 0:
                elapsed = time.time() - start
                rate = seq / elapsed if elapsed > 0 else 0
                print(f"  wrote {seq:,}/{args.packets:,} packets | {rate:,.0f} pkt/s")

        if buffer:
            f.write(buffer)

    elapsed = time.time() - start
    size_mb = os.path.getsize(args.out) / (1024 * 1024)

    print("Done.")
    print(f"Wrote {args.packets:,} packets to {args.out}")
    print(f"File size: {size_mb:.2f} MiB")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Generation rate: {args.packets / elapsed:,.0f} pkt/s")


if __name__ == "__main__":
    main()