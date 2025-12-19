import matplotlib.pyplot as plt
import os

class MapVisualizer:
    def __init__(self, size=(20, 20), output_dir="frames"):
        self.size = size
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_frame(self, turn, snapshot):
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(0, self.size[0])
        ax.set_ylim(0, self.size[1])
        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', alpha=0.5)

        for a_id, data in snapshot.items():
            if not data.get('alive') and not data.get('is_oni'): continue
            
            pos = data.get('pos', (0, 0))
            is_oni = data.get('is_oni', False)
            color = 'red' if is_oni else 'blue'
            marker = 'X' if is_oni else 'o'
            
            ax.scatter(pos[0] + 0.5, pos[1] + 0.5, c=color, marker=marker, s=150, edgecolors='black', zorder=3)
            ax.text(pos[0], pos[1] + 0.8, a_id, fontsize=9, fontweight='bold')

        plt.title(f"Simulation Turn: {turn:03}")
        plt.savefig(f"{self.output_dir}/frame_{turn:03}.png")
        plt.close()
