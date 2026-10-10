import os

import matplotlib.pyplot as plt


class URLMapVisualizer:
    def __init__(self, asset_urls=None, output_dir="frames"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_frame(self, turn, snapshot, grid, exit_pos):
        h, w = grid.shape
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.imshow(grid, cmap="Greys", vmin=0, vmax=1, interpolation="nearest")
        ey, ex = exit_pos
        ax.scatter([ex], [ey], marker="s", s=180, facecolors="none", edgecolors="green", linewidths=2)
        humans_x, humans_y, onis_x, onis_y, labels = [], [], [], [], []
        for a_id, status in snapshot.items():
            if not status.get("alive") or status.get("escaped"):
                continue
            y, x = status["pos"]
            if status.get("is_oni"):
                onis_x.append(x); onis_y.append(y)
            else:
                humans_x.append(x); humans_y.append(y)
            labels.append((a_id, x, y))
        if humans_x:
            ax.scatter(humans_x, humans_y, marker="o", s=80)
        if onis_x:
            ax.scatter(onis_x, onis_y, marker="X", s=100)
        for label, x, y in labels:
            ax.text(x + 0.18, y - 0.18, label, fontsize=6)
        ax.set_title(f"Turn {turn}")
        ax.set_xlim(-0.5, w-0.5); ax.set_ylim(h-0.5, -0.5)
        ax.set_xticks([]); ax.set_yticks([])
        fig.tight_layout()
        fig.savefig(os.path.join(self.output_dir, f"frame_{turn:03d}.png"), dpi=100)
        plt.close(fig)
