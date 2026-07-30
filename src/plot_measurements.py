#!/usr/bin/env python3
"""
Plot DVB-T2 measurement data from SQLite database.

Generates:
  1. Field strength by channel (bar chart)
  2. Geo scatter plot (lat/lon colored by field strength)
  3. Time series of measurements
  4. Per-channel frequency sweep (if multiple channels available)
"""

import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import init_db, get_recent_measurements, get_stats, _get_conn

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from collections import defaultdict

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "plots"


def fetch_all_measurements():
    """Fetch all measurements from DB."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.*, COUNT(r.id) as raw_count
        FROM measurements m
        LEFT JOIN raw_measurements r ON r.measurement_id = m.id
        GROUP BY m.id
        ORDER BY m.timestamp ASC
    """)
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def plot_field_strength_by_channel(measurements, output_dir):
    """Bar chart of field strength by channel name."""
    by_channel = defaultdict(list)
    for m in measurements:
        if m.get("field_strength_est_dbuvm") is not None:
            by_channel[m["channel_name"]].append(m["field_strength_est_dbuvm"])

    if not by_channel:
        print("  No field strength data")
        return

    channels = sorted(by_channel.keys())
    means = [sum(by_channel[c])/len(by_channel[c]) for c in channels]
    maxes = [max(by_channel[c]) for c in channels]
    mins = [min(by_channel[c]) for c in channels]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(channels))
    yerr = [
        [means[i] - mins[i] for i in range(len(channels))],
        [maxes[i] - means[i] for i in range(len(channels))],
    ]
    ax.bar(x, means, yerr=yerr,
           capsize=5, color="royalblue", alpha=0.8, label="Field Strength")
    ax.axhspan(39.5, 76.2, alpha=0.15, color="green", label="Rentang Acuan Komdigi (39.5–76.2)")
    ax.axhline(39.5, color="green", linestyle="--", alpha=0.5)
    ax.axhline(76.2, color="green", linestyle="--", alpha=0.5)

    for i, (ch, mean_val) in enumerate(zip(channels, means)):
        ax.annotate(f"{mean_val:.1f}", (i, mean_val), ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(channels, rotation=45, ha="right")
    ax.set_ylabel("Field Strength (dBµV/m)")
    ax.set_title("Estimasi Field Strength per Kanal DVB-T2")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    path = output_dir / "field_strength_by_channel.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_geo_map(measurements, output_dir):
    """Scatter plot of measurement locations colored by field strength."""
    points = []
    for m in measurements:
        lat = m.get("latitude")
        lon = m.get("longitude")
        fs = m.get("field_strength_est_dbuvm")
        if lat is not None and lon is not None and fs is not None:
            points.append((lat, lon, fs))

    if len(points) < 3:
        print("  Not enough geo points")
        return

    fig, ax = plt.subplots(figsize=(10, 8))
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    fs_vals = [p[2] for p in points]

    scatter = ax.scatter(lons, lats, c=fs_vals, cmap="RdYlGn", s=40,
                         edgecolors="black", linewidth=0.5, alpha=0.8)
    cbar = plt.colorbar(scatter, ax=ax, label="Field Strength (dBµV/m)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Lokasi Pengukuran DVB-T2")

    # Label clusters
    from collections import Counter
    lat_lon_counts = Counter(zip(lats, lons))
    for (lat, lon), cnt in lat_lon_counts.items():
        ax.annotate(f"  x{cnt}", (lon, lat), fontsize=7, alpha=0.6)

    path = output_dir / "measurement_geo_map.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_timeline(measurements, output_dir):
    """Time series of field strength measurements."""
    points = []
    for m in measurements:
        ts = m.get("timestamp")
        fs = m.get("field_strength_est_dbuvm")
        ch = m.get("channel_name", "?")
        if ts and fs is not None:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                points.append((dt, fs, ch))
            except ValueError:
                pass

    if len(points) < 3:
        print("  Not enough timeline points")
        return

    fig, ax = plt.subplots(figsize=(14, 5))
    times = [p[0] for p in points]
    vals = [p[1] for p in points]

    ax.scatter(times, vals, c="royalblue", s=15, alpha=0.7)
    ax.axhspan(39.5, 76.2, alpha=0.1, color="green", label="Rentang Acuan")
    ax.axhline(39.5, color="green", linestyle="--", alpha=0.4)
    ax.axhline(76.2, color="green", linestyle="--", alpha=0.4)
    ax.set_ylabel("Field Strength (dBµV/m)")
    ax.set_title("Timeline Pengukuran DVB-T2")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d\n%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.grid(alpha=0.3)

    path = output_dir / "measurement_timeline.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_frequency_sweep(measurements, output_dir):
    """Field strength vs frequency, colored by location."""
    points = []
    for m in measurements:
        freq = m.get("frequency_mhz")
        fs = m.get("field_strength_est_dbuvm")
        lat = m.get("latitude")
        if freq and fs is not None:
            location = "Jakarta" if lat and -6.5 < lat < -6.0 else "Purwokerto" if lat else "?"
            points.append((freq, fs, location))

    if len(points) < 3:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"Jakarta": "orange", "Purwokerto": "purple", "?": "gray"}
    for loc in set(p[2] for p in points):
        pts = [p for p in points if p[2] == loc]
        freqs = [p[0] for p in pts]
        fses = [p[1] for p in pts]
        ax.scatter(freqs, fses, c=colors.get(loc, "gray"), label=loc, s=40, alpha=0.7)

    ax.axhspan(39.5, 76.2, alpha=0.1, color="green", label="Rentang Acuan")
    ax.set_xlabel("Frekuensi (MHz)")
    ax.set_ylabel("Field Strength (dBµV/m)")
    ax.set_title("Field Strength vs Frekuensi per Lokasi")
    ax.legend()
    ax.grid(alpha=0.3)

    path = output_dir / "frequency_sweep.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    measurements = fetch_all_measurements()
    stats = get_stats()

    print(f"=== DVB-T2 Measurement Report ===")
    print(f"  Total measurements: {stats['total_measurements']}")
    print(f"  Total raw readings: {stats['total_raw_readings']}")
    print(f"  Date range: {stats['first_measurement']} to {stats['last_measurement']}")
    print(f"  Unique channels: {stats['unique_channels']}")
    if stats['category_counts']:
        for cat, cnt in stats['category_counts'].items():
            print(f"    {cat}: {cnt}")
    print()

    if not measurements:
        print("  No data to plot")
        return

    plots = []
    plots.append(plot_field_strength_by_channel(measurements, OUTPUT_DIR))
    plots.append(plot_geo_map(measurements, OUTPUT_DIR))
    plots.append(plot_timeline(measurements, OUTPUT_DIR))
    plots.append(plot_frequency_sweep(measurements, OUTPUT_DIR))

    plots = [p for p in plots if p]
    print(f"\n  Generated {len(plots)} plots in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
