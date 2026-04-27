#!/usr/bin/env python3
import argparse
import re

ACTUAL_RE = re.compile(
    r"Actual:\s+(\d+)\s+packets\s+\((\d+)\s+bytes\)\s+sent\s+in\s+([0-9.]+)\s+seconds"
)

RATE_RE = re.compile(
    r"Rated:\s+([0-9.]+)\s+Bps,\s+([0-9.]+)\s+Mbps,\s+([0-9.]+)\s+pps"
)


def parse_log(path: str):
    samples = []
    pending_actual = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            actual_match = ACTUAL_RE.search(line)
            if actual_match:
                pending_actual = {
                    "packets": int(actual_match.group(1)),
                    "bytes": int(actual_match.group(2)),
                    "seconds": float(actual_match.group(3)),
                    "bps": None,
                    "mbps": None,
                    "pps": None,
                }
                samples.append(pending_actual)
                continue

            rate_match = RATE_RE.search(line)
            if rate_match and pending_actual is not None:
                pending_actual["bps"] = float(rate_match.group(1))
                pending_actual["mbps"] = float(rate_match.group(2))
                pending_actual["pps"] = float(rate_match.group(3))

    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--target-mbps", type=float, required=True)
    args = parser.parse_args()

    samples = parse_log(args.log)
    if len(samples) < 2:
        raise SystemExit("Need at least two Actual samples")

    final = samples[-1]
    prev = samples[-2]

    target_bps = args.target_mbps * 1_000_000 / 8

    expected_total_seconds = final["bytes"] / target_bps
    early_seconds = expected_total_seconds - final["seconds"]

    delta_packets = final["packets"] - prev["packets"]
    delta_bytes = final["bytes"] - prev["bytes"]
    delta_seconds = final["seconds"] - prev["seconds"]
    delta_mbps = (delta_bytes * 8 / delta_seconds) / 1_000_000 if delta_seconds > 0 else float("inf")
    expected_delta_seconds = delta_bytes / target_bps

    print(f"log: {args.log}")
    print(f"samples: {len(samples)}")
    print()
    print("final:")
    print(f"  packets: {final['packets']:,}")
    print(f"  bytes:   {final['bytes']:,}")
    print(f"  seconds: {final['seconds']:.2f}")
    print(f"  rated:   {final['mbps']} Mbps")
    print()
    print("expected:")
    print(f"  target Mbps:              {args.target_mbps:.2f}")
    print(f"  expected total seconds:   {expected_total_seconds:.2f}")
    print(f"  observed total seconds:   {final['seconds']:.2f}")
    print(f"  finished early by:        {early_seconds:.2f}s")
    print()
    print("last interval:")
    print(f"  previous packets:         {prev['packets']:,}")
    print(f"  final packets:            {final['packets']:,}")
    print(f"  delta packets:            {delta_packets:,}")
    print(f"  delta bytes:              {delta_bytes:,}")
    print(f"  observed delta seconds:   {delta_seconds:.2f}")
    print(f"  expected delta seconds:   {expected_delta_seconds:.2f}")
    print(f"  observed interval Mbps:   {delta_mbps:.2f}")


if __name__ == "__main__":
    main()