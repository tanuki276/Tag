import os

import matplotlib.pyplot as plt


class URLMapVisualizer:
    def __init__(self, asset_urls=None, output_dir="frames"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save_frame(
        self,
        turn,
        snapshot,
        grid,
        exit_pos,
        grid_items=None,
        exit_open=False,
    ):
        h, w = grid.shape
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.imshow(grid, cmap="Greys", vmin=0, vmax=1, interpolation="nearest")

        ey, ex = exit_pos
        ax.scatter(
            [ex],
            [ey],
            marker="s",
            s=180,
            facecolors="tab:green" if exit_open else "none",
            edgecolors="tab:green",
            linewidths=2,
        )

        if grid_items:
            key_x, key_y, doll_x, doll_y, mp_x, mp_y = [], [], [], [], [], []
            for pos, element in grid_items.items():
                if element.kind == "EXIT":
                    continue
                y, x = pos
                if element.kind == "KEY":
                    key_x.append(x)
                    key_y.append(y)
                elif element.kind == "DOLL":
                    doll_x.append(x)
                    doll_y.append(y)
                elif element.kind == "MP_POTION":
                    mp_x.append(x)
                    mp_y.append(y)

            if key_x:
                ax.scatter(key_x, key_y, marker="*", s=80, c="gold", edgecolors="black", linewidths=0.4)
            if doll_x:
                ax.scatter(doll_x, doll_y, marker="D", s=50, c="tab:purple")
            if mp_x:
                ax.scatter(mp_x, mp_y, marker="P", s=55, c="tab:cyan")

        humans_x, humans_y, onis_x, onis_y, labels = [], [], [], [], []
        escaped = 0
        dead = 0
        identified_keys = 0

        for a_id, status in snapshot.items():
            if not status.get("is_oni"):
                identified_keys += int(status.get("keys_identified", 0))
                if status.get("escaped"):
                    escaped += 1
                if not status.get("alive"):
                    dead += 1

            if not status.get("alive") or status.get("escaped"):
                continue

            y, x = status["pos"]
            if status.get("is_oni"):
                onis_x.append(x)
                onis_y.append(y)
                role = status.get("role")
                suffix = f":{str(role)[:1]}" if role else ""
            else:
                humans_x.append(x)
                humans_y.append(y)
                suffix = ":O" if status.get("job") == "ORACLE" else ""

            if status.get("blocked_turns", 0) >= 3 and not status.get("is_oni"):
                suffix += "!"

            labels.append((f"{a_id}{suffix}", x, y))

        if humans_x:
            ax.scatter(humans_x, humans_y, marker="o", s=80, c="tab:blue")
        if onis_x:
            ax.scatter(onis_x, onis_y, marker="X", s=100, c="tab:orange")

        for label, x, y in labels:
            ax.text(x + 0.18, y - 0.18, label, fontsize=6)

        active_humans = sum(
            1
            for status in snapshot.values()
            if not status.get("is_oni")
            and status.get("alive")
            and not status.get("escaped")
        )
        exit_text = "OPEN" if exit_open else "CLOSED"
        hud = (
            f"Human {active_humans}  Escaped {escaped}  Dead {dead}\n"
            f"Keys identified {identified_keys}  Exit {exit_text}\n"
            "* Key   D Doll   P MP Potion   ! blocked"
        )

        ax.set_title(f"Turn {turn}")
        ax.text(
            0.01,
            0.99,
            hud,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        )
        ax.set_xlim(-0.5, w - 0.5)
        ax.set_ylim(h - 0.5, -0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        fig.savefig(os.path.join(self.output_dir, f"frame_{turn:03d}.png"), dpi=100)
        plt.close(fig)
