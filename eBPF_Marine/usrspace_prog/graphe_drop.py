from ddos_user_space import stats_queue, start_detection
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

window = 30
data = deque([0]*window, maxlen=window)

def moving_average(data, window=5):
    if len(data) < window:
        return data
    return np.convolve(data, np.ones(window)/window, mode='valid')

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [], color='red', linewidth=2)
text = ax.text(0.95, 0.95, "", transform=ax.transAxes, ha='right', va='top', fontsize=9, color='red')
ax.set_title("Taux de paquets bloqués (%)")
ax.set_ylabel("Drop (%)")
ax.set_xlabel("Temps (s)")
ax.grid(True, linestyle='--')

start_detection()

while True:
    _, drop, *_ = stats_queue.get()
    data.append(drop)

    smoothed = moving_average(list(data))
    line.set_ydata(smoothed)
    line.set_xdata(np.arange(len(smoothed)))
    ax.relim()
    ax.autoscale_view()
    text.set_text(f"Drop\nMoy: {np.mean(data):.2f}%\nActu: {data[-1]:.2f}%")
    plt.pause(0.01)
    fig.savefig("userspace_ddos_drop.png")
