import os
from io import BytesIO
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from typing import Dict, Tuple, List
from pkg.schema.models import ActorStatus

class URLMapVisualizer:
    def __init__(self, asset_urls: Dict[str, List[str]], output_dir: str = "frames"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.imgs = {key: self._fetch_strictly(urls, key) for key, urls in asset_urls.items()}

    def _fetch_strictly(self, urls: List[str], name: str):
        for url in urls:
            try:
                resp = requests.get(url, timeout=5.0)
                resp.raise_for_status()
                return mpimg.imread(BytesIO(resp.content))
            except Exception:
                continue
        raise RuntimeError(f"CRITICAL_ASSET_MISSING: {name}")

    def save_frame(self, turn: int, snapshot: Dict[str, ActorStatus], grid: np.ndarray, exit_pos: Tuple[int, int]):
        h, w = grid.shape
        fig, ax = plt.subplots(figsize=(w * 0.5, h * 0.5))
        ax.set_xlim(0, w)
        ax.set_ylim(0, h)
        ax.axis('off')

        for y in range(h):
            for x in range(w):
                py = h - y - 1
                tile = "wall" if grid[y, x] == 1 else "floor"
                ax.imshow(self.imgs[tile], extent=(x, x + 1, py, py + 1), zorder=0)

        ey, ex = exit_pos
        ax.imshow(self.imgs["exit"], extent=(ex, ex + 1, h - ey - 1, h - ey), zorder=1)

        for a_id, status in snapshot.items():
            if status.pos is None or not status.alive or status.escaped:
                continue
            
            ay, ax_pos = status.pos
            img_key = "oni" if status.is_oni else "human"
            py = h - ay - 1
            
            ax.imshow(self.imgs[img_key], extent=(ax_pos, ax_pos + 1, py, py + 1), zorder=2)
            ax.text(ax_pos + 0.5, py + 1.1, a_id, 
                    ha='center', va='bottom', fontsize=9, color='yellow',
                    fontweight='bold', bbox=dict(facecolor='black', alpha=0.7, lw=0, pad=1))

        plt.savefig(os.path.join(self.output_dir, f"frame_{turn:03}.png"), 
                    bbox_inches='tight', pad_inches=0, dpi=120)
        plt.close(fig)
