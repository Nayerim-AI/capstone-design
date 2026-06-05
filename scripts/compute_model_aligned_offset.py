#!/usr/bin/env python3
"""Hitung offset model-aligned dari RadioPlanner anchor point.

Offset ini BUKAN kalibrasi absolut. RadioPlanner adalah model/simulasi,
bukan field strength meter atau spectrum analyzer terkalibrasi.
"""
import argparse


def compute_model_aligned_offset(raw_bandpower_db, radioplanner_dbuvm):
    return float(radioplanner_dbuvm) - float(raw_bandpower_db)


def main():
    parser = argparse.ArgumentParser(
        description="Hitung CALIBRATION_OFFSET_DB model-aligned dari RadioPlanner anchor point."
    )
    parser.add_argument("--raw-bandpower-db", type=float, required=True, help="Raw bandpower alat di anchor point")
    parser.add_argument("--radioplanner-dbuvm", type=float, required=True, help="Field strength RadioPlanner di anchor point")
    args = parser.parse_args()

    offset = compute_model_aligned_offset(args.raw_bandpower_db, args.radioplanner_dbuvm)

    print("=== RadioPlanner Model-Aligned Offset ===")
    print(f"raw_bandpower_db = {args.raw_bandpower_db:.2f} dB")
    print(f"radioplanner_dbuvm = {args.radioplanner_dbuvm:.2f} dBµV/m")
    print(f"offset_model_db = {offset:.2f} dB")
    print("")
    print("Rekomendasi .env / config:")
    print("CALIBRATION_MODE=radioplanner_model_aligned")
    print(f"CALIBRATION_OFFSET_DB={offset:.2f}")
    print("CALIBRATION_SOURCE=RadioPlanner anchor point; isi tanggal/lokasi")
    print("")
    print("Catatan: offset ini bukan kalibrasi absolut. RadioPlanner adalah pembanding model/simulasi, bukan alat ukur profesional.")


if __name__ == "__main__":
    main()
