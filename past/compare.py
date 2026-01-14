import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Load
orig_rate, orig = wavfile.read("MXLamAMF.wav")
if len(orig.shape) > 1:
    orig = orig.mean(axis=1)

# AM conversion
audio = orig.astype(np.float32) / 255.0
sample_rate = 100000
audio = resample(audio, int(len(audio) * sample_rate / orig_rate)).astype(np.float32)
# actual modulating formula
# s(t)=Ac[1+μcos(2πfmt)]cos(2πfct)

modulated = 0.5 * (1.0 + 0.8 * (audio - 0.5) * 2)
modulated = np.clip(modulated, 0, 1)
output = (modulated * 32767).astype(np.int16)

orig_len = len(orig)
am_len = len(output)

# Define all regions
# Envelope regions (wider)
peak_start_o, peak_end_o = 0, 4000
peak_start, peak_end = 0, 100000

trough_start_o, trough_end_o = 2000, 6000
trough_start, trough_end = 50000, 150000

trans_start_o, trans_end_o = 6000, 10000
trans_start, trans_end = 150000, 250000

# Detail regions (tight zoom)
detail_start_o, detail_end_o = 1000, 1100
detail_start, detail_end = 25000, 28000

ymin_o, ymax_o = 0, 260
ymin, ymax = 0, 32000

# === FILE 1: FULL WAVEFORM WITH ALL REGIONS HIGHLIGHTED ===
fig1, axes1 = plt.subplots(2, 1, figsize=(14, 8))

axes1[0].plot(orig, color='#1f77b4')
axes1[0].axhline(y=128, color='gray', linestyle='--', alpha=0.5)
axes1[0].set_title("Original Audio - Full Waveform")
axes1[0].set_ylabel("Amplitude")
axes1[0].set_xlabel("Samples")
# Add region boxes
rect_p = Rectangle((peak_start_o, ymin_o), peak_end_o - peak_start_o, ymax_o,
                    linewidth=2, edgecolor='red', facecolor='red', alpha=0.15)
rect_t = Rectangle((trough_start_o, ymin_o), trough_end_o - trough_start_o, ymax_o,
                    linewidth=2, edgecolor='orange', facecolor='orange', alpha=0.15)
rect_tr = Rectangle((trans_start_o, ymin_o), trans_end_o - trans_start_o, ymax_o,
                     linewidth=2, edgecolor='green', facecolor='green', alpha=0.15)
rect_d = Rectangle((detail_start_o, ymin_o), detail_end_o - detail_start_o, ymax_o,
                    linewidth=2, edgecolor='purple', facecolor='purple', alpha=0.15)
axes1[0].add_patch(rect_p)
axes1[0].add_patch(rect_t)
axes1[0].add_patch(rect_tr)
axes1[0].add_patch(rect_d)
axes1[0].text(peak_start_o + 100, ymax_o - 20, "Peak", fontsize=10, fontweight='bold', color='red')
axes1[0].text(trough_start_o + 100, ymax_o - 40, "Trough", fontsize=10, fontweight='bold', color='orange')
axes1[0].text(trans_start_o + 100, ymax_o - 20, "Transition", fontsize=10, fontweight='bold', color='green')
axes1[0].text(detail_start_o, ymax_o - 60, "Detail", fontsize=10, fontweight='bold', color='purple')

axes1[1].plot(output, color='#1f77b4')
axes1[1].axhline(y=16384, color='r', linestyle='--', label="Carrier", alpha=0.7)
axes1[1].set_title("AM Modulated Output - Full Waveform")
axes1[1].set_ylabel("Amplitude")
axes1[1].set_xlabel("Samples")
axes1[1].legend(loc='upper right')
# Add region boxes
rect_p2 = Rectangle((peak_start, ymin), peak_end - peak_start, ymax,
                     linewidth=2, edgecolor='red', facecolor='red', alpha=0.15)
rect_t2 = Rectangle((trough_start, ymin), trough_end - trough_start, ymax,
                     linewidth=2, edgecolor='orange', facecolor='orange', alpha=0.15)
rect_tr2 = Rectangle((trans_start, ymin), trans_end - trans_start, ymax,
                      linewidth=2, edgecolor='green', facecolor='green', alpha=0.15)
rect_d2 = Rectangle((detail_start, ymin), detail_end - detail_start, ymax,
                     linewidth=2, edgecolor='purple', facecolor='purple', alpha=0.15)
axes1[1].add_patch(rect_p2)
axes1[1].add_patch(rect_t2)
axes1[1].add_patch(rect_tr2)
axes1[1].add_patch(rect_d2)
axes1[1].text(peak_start + 2000, ymax - 2000, "Peak", fontsize=10, fontweight='bold', color='red')
axes1[1].text(trough_start + 2000, ymax - 4000, "Trough", fontsize=10, fontweight='bold', color='orange')
axes1[1].text(trans_start + 2000, ymax - 2000, "Transition", fontsize=10, fontweight='bold', color='green')
axes1[1].text(detail_start, ymax - 6000, "Detail", fontsize=10, fontweight='bold', color='purple')

plt.tight_layout()
fig1.savefig("full_waveform.png", dpi=150)
print("Saved: full_waveform.png")
plt.close(fig1)

# === FILE 2: ZOOMED REGIONS - ENVELOPE VIEW ===
fig2, axes2 = plt.subplots(3, 2, figsize=(16, 12))

# Row 1: Peak (red)
axes2[0, 0].plot(orig, color='#1f77b4')
axes2[0, 0].set_title("Original - Peak Region", color='red', fontweight='bold')
axes2[0, 0].set_ylabel("Amplitude")
axes2[0, 0].set_xlim(peak_start_o, peak_end_o)
axes2[0, 0].set_ylim(ymin_o, ymax_o)

axes2[0, 1].plot(output, color='#1f77b4')
axes2[0, 1].set_title("AM Output - Peak Region", color='red', fontweight='bold')
axes2[0, 1].set_ylabel("Amplitude")
axes2[0, 1].set_xlim(peak_start, peak_end)
axes2[0, 1].set_ylim(ymin, ymax)
axes2[0, 1].axhline(y=16384, color='r', linestyle='--', label="Carrier", alpha=0.7)
axes2[0, 1].legend(loc='upper right')

# Row 2: Trough (orange)
axes2[1, 0].plot(orig, color='#1f77b4')
axes2[1, 0].set_title("Original - Trough Region", color='orange', fontweight='bold')
axes2[1, 0].set_ylabel("Amplitude")
axes2[1, 0].set_xlim(trough_start_o, trough_end_o)
axes2[1, 0].set_ylim(ymin_o, ymax_o)

axes2[1, 1].plot(output, color='#1f77b4')
axes2[1, 1].set_title("AM Output - Trough Region", color='orange', fontweight='bold')
axes2[1, 1].set_ylabel("Amplitude")
axes2[1, 1].set_xlim(trough_start, trough_end)
axes2[1, 1].set_ylim(ymin, ymax)
axes2[1, 1].axhline(y=16384, color='r', linestyle='--', label="Carrier", alpha=0.7)
axes2[1, 1].legend(loc='upper right')

# Row 3: Transition (green)
axes2[2, 0].plot(orig, color='#1f77b4')
axes2[2, 0].set_title("Original - Transition Region", color='green', fontweight='bold')
axes2[2, 0].set_xlabel("Samples")
axes2[2, 0].set_ylabel("Amplitude")
axes2[2, 0].set_xlim(trans_start_o, trans_end_o)
axes2[2, 0].set_ylim(ymin_o, ymax_o)

axes2[2, 1].plot(output, color='#1f77b4')
axes2[2, 1].set_title("AM Output - Transition Region", color='green', fontweight='bold')
axes2[2, 1].set_xlabel("Samples")
axes2[2, 1].set_ylabel("Amplitude")
axes2[2, 1].set_xlim(trans_start, trans_end)
axes2[2, 1].set_ylim(ymin, ymax)
axes2[2, 1].axhline(y=16384, color='r', linestyle='--', label="Carrier", alpha=0.7)
axes2[2, 1].legend(loc='upper right')

plt.tight_layout()
fig2.savefig("zoomed_regions.png", dpi=150)
print("Saved: zoomed_regions.png")
plt.close(fig2)

# === FILE 3: CARRIER DETAIL (purple) ===
fig3, axes3 = plt.subplots(2, 1, figsize=(14, 8))

axes3[0].plot(range(detail_start_o, detail_end_o), orig[detail_start_o:detail_end_o], color='#1f77b4')
axes3[0].set_title("Original - Detail Region", color='purple', fontweight='bold')
axes3[0].set_ylabel("Amplitude")
axes3[0].set_xlabel("Samples")
axes3[0].set_ylim(ymin_o, ymax_o)

axes3[1].plot(range(detail_start, detail_end), output[detail_start:detail_end], color='#1f77b4')
axes3[1].axhline(y=16384, color='r', linestyle='--', label="Carrier", alpha=0.7)
axes3[1].set_title("AM Output - Detail Region", color='purple', fontweight='bold')
axes3[1].set_xlabel("Samples")
axes3[1].set_ylabel("Amplitude")
axes3[1].set_ylim(ymin, ymax)
axes3[1].legend(loc='upper right')

plt.tight_layout()
fig3.savefig("carrier_detail.png", dpi=150)
print("Saved: carrier_detail.png")
plt.close(fig3)

print("\nDone! Three files:")
print("  - full_waveform.png (overview with all regions highlighted)")
print("  - zoomed_regions.png (peak/trough/transition)")
print("  - carrier_detail.png (individual oscillations)")