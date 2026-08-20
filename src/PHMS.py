import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import deque
import customtkinter as ctk
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

# Set UI Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
ctk.deactivate_automatic_dpi_awareness()

V_PI = -3.725  # Volts required for pi phase shift

STATE_CONFIGS = {
    "BS": {
        "label": "Bar State (BS)",
        "color": "#F75D59",
        "edge": "#922B21",
        "tpH_v": V_PI,
        "tpH_p": np.pi,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Bar T_|| = 1.0, Cross T_X = 0.0",
    },
    "CS": {
        "label": "Cross State (CS)",
        "color": "#7FB3D5",
        "edge": "#1B4F72",
        "tpH_v": 0.0,
        "tpH_p": 0.0,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Bar T_|| = 0.0, Cross T_X = 1.0",
    },
    "TC": {
        "label": "Tunable Coupler (TC)",
        "color": "#FAD02C",
        "edge": "#B7950B",
        "tpH_v": V_PI / np.sqrt(2),
        "tpH_p": np.pi / 2.0,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "50:50 Power Splitter (T_|| = 0.5, T_X = 0.5)",
    },
    "AV": {
        "label": "Available, Not used (AV)",
        "color": "#7F8C8D",
        "edge": "#34495E",
        "tpH_v": 0.0,
        "tpH_p": 0.0,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Idle / Unconfigured unrouted state",
    },
    "DEF_BS": {
        "label": "Defect: Stuck Bar",
        "color": "#800000",
        "edge": "#4A2311",
        "tpH_v": 0.0,
        "tpH_p": 0.0,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Hardware Fault: Locked permanently in Bar state",
    },
    "DEF_CS": {
        "label": "Defect: Stuck Cross",
        "color": "#000080",
        "edge": "#11224A",
        "tpH_v": V_PI,
        "tpH_p": np.pi,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Hardware Fault: Locked permanently in Cross state",
    },
    "DEF_DEAD": {
        "label": "Defect: Dead/Opaque",
        "color": "#111111",
        "edge": "#000000",
        "tpH_v": 0.0,
        "tpH_p": 0.0,
        "btH_v": 0.0,
        "btH_p": 0.0,
        "desc": "Hardware Fault: Opaque (Blocks all optical signals)",
    },
}


# =====================================================================
# PHYSICAL GRAPH & OPTICAL ROUTING ENGINE
# =====================================================================
class PhotonicMeshGraph:
    def __init__(self, mzi_data, port_connections, open_ports):
        self.mzi_data = mzi_data
        self.port_connections = port_connections
        self.open_ports = set(open_ports)
        self.adjacency_list = {}
        self.node_attributes = {}
        self.build_graph()

    def add_edge(self, u, v, weight=1.0, edge_type="waveguide"):
        self.adjacency_list.setdefault(u, []).append({
            "target": v,
            "weight": weight,
            "type": edge_type,
        })

    def build_graph(self):
        self.adjacency_list.clear()
        self.node_attributes.clear()

        for tag, d in self.mzi_data.items():
            for p in ["Opt1", "Opt2", "Opt3", "Opt4"]:
                p_id = f"{tag}_{p}"
                self.node_attributes[p_id] = {
                    "mzi": tag,
                    "port": p,
                    "is_open": p_id in self.open_ports,
                    "state": d["state"],
                    "tpH_v": d["tpH_v"],
                    "btH_v": d["btH_v"],
                }
                self.adjacency_list[p_id] = []

        for tag, d in self.mzi_data.items():
            state = d["state"]
            p1, p2, p3, p4 = f"{tag}_Opt1", f"{tag}_Opt2", f"{tag}_Opt3", f"{tag}_Opt4"

            # CRITICAL FIX: ANY defect state (DEF_BS, DEF_CS, DEF_DEAD) is an absolute physical wall.
            # Do NOT add internal transmission edges so routers cannot pass through them.
            if state.startswith("DEF_"):
                continue

            if state == "BS":
                self.add_edge(p1, p3, 1.0, "mzi_bar")
                self.add_edge(p2, p4, 1.0, "mzi_bar")
                self.add_edge(p3, p1, 1.0, "mzi_bar")
                self.add_edge(p4, p2, 1.0, "mzi_bar")
            elif state == "CS":
                self.add_edge(p1, p4, 1.0, "mzi_cross")
                self.add_edge(p2, p3, 1.0, "mzi_cross")
                self.add_edge(p4, p1, 1.0, "mzi_cross")
                self.add_edge(p3, p2, 1.0, "mzi_cross")
            elif state == "TC":
                for src in [p1, p2]:
                    for dst in [p3, p4]:
                        self.add_edge(src, dst, 0.5, "mzi_split")
                        self.add_edge(dst, src, 0.5, "mzi_split")
            elif state == "AV":
                self.add_edge(p1, p3, 1.0, "mzi_bar")
                self.add_edge(p2, p4, 1.0, "mzi_bar")
                self.add_edge(p1, p4, 1.0, "mzi_cross")
                self.add_edge(p2, p3, 1.0, "mzi_cross")
                self.add_edge(p3, p1, 1.0, "mzi_bar")
                self.add_edge(p4, p2, 1.0, "mzi_bar")
                self.add_edge(p4, p1, 1.0, "mzi_cross")
                self.add_edge(p3, p2, 1.0, "mzi_cross")

        for p_src, p_dst in self.port_connections.items():
            self.add_edge(p_src, p_dst, 1.0, "waveguide_link")

    def find_multipaths(self, start_port, end_port, constraint_mode="AV_ONLY", max_paths=5, max_depth=40, target_length=None):
        if start_port not in self.node_attributes or end_port not in self.node_attributes:
            return [], "Start or Destination port does not exist in mesh."

        if start_port == end_port:
            return [], "Source and Destination ports cannot be identical."

        start_mzi, start_p = start_port.rsplit("_", 1)
        end_mzi, end_p = end_port.rsplit("_", 1)

        same_side = (
            (start_mzi == end_mzi) and 
            ((start_p in ["Opt1", "Opt2"] and end_p in ["Opt1", "Opt2"]) or 
             (start_p in ["Opt3", "Opt4"] and end_p in ["Opt3", "Opt4"]))
        )

        queue = deque([(start_port, [start_port], {}, {}, {start_port})])
        found_paths = []

        while queue and len(found_paths) < max_paths:
            curr_port, path, state_map, used_mzis, visited = queue.popleft()
            current_len = len(path) - 1

            if target_length is not None and current_len > target_length:
                continue
            if target_length is None and current_len > max_depth:
                continue

            if curr_port == end_port:
                if same_side and current_len <= 3:
                    continue
                if target_length is not None:
                    if current_len == target_length:
                        found_paths.append({"path": path, "states": state_map})
                else:
                    found_paths.append({"path": path, "states": state_map})
                continue

            parent_mzi, p_name = curr_port.rsplit("_", 1)
            mzi_info = self.mzi_data.get(parent_mzi, {})
            current_mzi_state = mzi_info.get("state", "AV")

            # Block traversal if current or parent is a defect
            if current_mzi_state.startswith("DEF_"):
                continue

            transitions = []
            direction = None
            if p_name in ["Opt1", "Opt2"]:
                direction = "LR"
                transitions = [
                    ("Opt3", "BS" if p_name == "Opt1" else "CS"),
                    ("Opt4", "CS" if p_name == "Opt1" else "BS")
                ]
            elif p_name in ["Opt3", "Opt4"]:
                direction = "RL"
                transitions = [
                    ("Opt1", "BS" if p_name == "Opt3" else "CS"),
                    ("Opt2", "CS" if p_name == "Opt3" else "BS")
                ]

            if parent_mzi not in used_mzis:
                for out_p, req_state in transitions:
                    target_port = f"{parent_mzi}_{out_p}"

                    # Double check target MZI isn't defective
                    target_mzi_state = self.mzi_data.get(parent_mzi, {}).get("state", "AV")
                    if target_mzi_state.startswith("DEF_"):
                        continue

                    # Normal Soft Routing Constraints
                    if constraint_mode == "AV_ONLY" and current_mzi_state != "AV":
                        continue
                    elif constraint_mode == "SHARED":
                        if current_mzi_state not in ["AV", req_state]:
                            continue
                    elif constraint_mode == "ANY":
                        pass 

                    if target_port not in visited:
                        new_visited = set(visited)
                        new_visited.add(target_port)

                        new_state_map = dict(state_map)
                        new_state_map[parent_mzi] = req_state

                        new_used_mzis = dict(used_mzis)
                        new_used_mzis[parent_mzi] = direction

                        queue.append((target_port, path + [target_port], new_state_map, new_used_mzis, new_visited))

            if curr_port in self.port_connections:
                nxt_port = self.port_connections[curr_port]
                nxt_mzi = nxt_port.rsplit("_", 1)[0]

                # Ensure next MZI isn't defective
                if self.mzi_data.get(nxt_mzi, {}).get("state", "AV").startswith("DEF_"):
                    continue

                if nxt_mzi not in used_mzis or nxt_port == end_port:
                    if nxt_port not in visited:
                        new_visited = set(visited)
                        new_visited.add(nxt_port)
                        queue.append((nxt_port, path + [nxt_port], dict(state_map), dict(used_mzis), new_visited))

        if not found_paths:
            return [], "No viable forward-progressing optical path found matching the selected constraints."
        
        found_paths.sort(key=lambda x: len(x["path"]))
        return found_paths, "Success"

    def export_graph_json(self):
        return {
            "graph_type": "LoopFree_Photonic_Mesh_Network",
            "total_nodes": len(self.node_attributes),
            "open_boundary_ports": list(self.open_ports),
            "nodes": self.node_attributes,
            "edges": self.adjacency_list,
        }


# =====================================================================
# MAIN GUI APPLICATION
# =====================================================================
class PhotonicMeshStudio(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Photonic Hexagonal Mesh Studio (TBU Controller)")
        self.geometry("1560x950")
        self.minsize(1200, 750)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Mesh Grid Defaults
        self.num_cols = 4
        self.num_rows = 4
        self.L = 1.1
        self.w = 0.40
        self.port_len = 0.25
        self.port_sep = 0.22
        self.node_gap = 0.20

        self.mzi_data = {}
        self.patches_dict = {}
        self.port_artists = {}
        self.port_coords = {}
        self.selected_mzi = None
        self.selected_port_circle = None
        self.open_ports_set = set()
        self.port_connections = {}
        self.graph = None
        self.is_modified = False
        
        self.active_route_lines = []
        self.alt_route_lines = []
        self.last_computed_paths = []
        self.selected_path_idx = 0

        # Matrix Compiler State
        self.matrix_connections = []
        self.matrix_route_lines = []
        self.matrix_preview_states = None

        # Interactive Picking Mode: None, "SRC", "DST", "MATRIX_SRC", "MATRIX_DST"
        self.picking_target = None
        self.src_highlight_circle = None
        self.dst_highlight_circle = None

        # Color Palette for Multiple Channels
        self.channel_colors = ["#FF5733", "#33FF57", "#3357FF", "#F033FF", "#33FFF0", "#F0FF33", "#FFA833"]

        # Hex Geometry Math
        self.angle = np.pi / 3
        self.cos60 = np.cos(self.angle)
        self.sin60 = np.sin(self.angle)
        self._update_geometry_math()

        self._init_mesh_data()
        self._build_main_layout()
        self._select_mzi("MZI_1_1_in")

    def _update_geometry_math(self):
        self.arm_span = self.L + 2.0 * self.port_len + 2.0 * self.node_gap
        self.dx = self.arm_span * (1.0 + self.cos60)
        self.dy = 2.0 * self.arm_span * self.sin60

    def _init_mesh_data(self):
        self.mzi_data.clear()
        for m in range(1, self.num_cols + 1):
            for n in range(1, self.num_rows + 1):
                for direction in ["in", "up", "down"]:
                    tag = f"MZI_{m}_{n}_{direction}"
                    cfg = STATE_CONFIGS["AV"]
                    self.mzi_data[tag] = {
                        "m": m,
                        "n": n,
                        "dir": direction,
                        "state": "AV",
                        "tpH_v": cfg["tpH_v"],
                        "tpH_p": cfg["tpH_p"],
                        "btH_v": cfg["btH_v"],
                        "btH_p": cfg["btH_p"],
                        "tpH_pin": f"PORT_{m}_{n}_{direction}_tpH",
                        "btH_pin": f"PORT_{m}_{n}_{direction}_btH",
                    }

    def _on_close(self):
        if self.is_modified:
            resp = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes in the Photonic Mesh configuration.\n\nDo you want to save them before exiting?",
            )
            if resp is None:
                return
            elif resp:
                saved = self._save_json()
                if not saved:
                    return

        try:
            plt.close("all")
            self.quit()
            self.destroy()
        except Exception:
            pass

    # -------------------------------------------------------------
    # Optical Node Connectivity Engine
    # -------------------------------------------------------------
    def _build_topology_connections(self):
        nodes = {}

        for m in range(1, self.num_cols + 1):
            y_offset_col = (m % 2) * (self.dy / 2.0)
            for n in range(1, self.num_rows + 1):
                v_x = (m - 1) * self.dx
                v_y = -(n - 1) * self.dy - y_offset_col

                p_in_left = (round(v_x - self.arm_span, 3), round(v_y, 3))
                p_in_right = (round(v_x, 3), round(v_y, 3))
                nodes.setdefault(p_in_left, []).append({"tag": f"MZI_{m}_{n}_in", "end": "L", "ray_deg": 0.0})
                nodes.setdefault(p_in_right, []).append({"tag": f"MZI_{m}_{n}_in", "end": "R", "ray_deg": 180.0})

                p_up_left = (round(v_x, 3), round(v_y, 3))
                p_up_right = (round(v_x + self.arm_span * self.cos60, 3), round(v_y + self.arm_span * self.sin60, 3))
                nodes.setdefault(p_up_left, []).append({"tag": f"MZI_{m}_{n}_up", "end": "L", "ray_deg": 60.0})
                nodes.setdefault(p_up_right, []).append({"tag": f"MZI_{m}_{n}_up", "end": "R", "ray_deg": 240.0})

                p_down_left = (round(v_x, 3), round(v_y, 3))
                p_down_right = (round(v_x + self.arm_span * self.cos60, 3), round(v_y - self.arm_span * self.sin60, 3))
                nodes.setdefault(p_down_left, []).append({"tag": f"MZI_{m}_{n}_down", "end": "L", "ray_deg": 300.0})
                nodes.setdefault(p_down_right, []).append({"tag": f"MZI_{m}_{n}_down", "end": "R", "ray_deg": 120.0})

        connections = {}
        connected_ports = set()

        def link(p1, p2):
            connections[p1] = p2
            connections[p2] = p1
            connected_ports.add(p1)
            connected_ports.add(p2)

        for _, arms in nodes.items():
            if len(arms) < 2:
                continue

            arms.sort(key=lambda a: a["ray_deg"])
            num_arms = len(arms)

            for i in range(num_arms):
                arm_a = arms[i]
                arm_b = arms[(i + 1) % num_arms]

                d_theta = (arm_b["ray_deg"] - arm_a["ray_deg"]) % 360.0

                if 115.0 <= d_theta <= 125.0:
                    p_a = f"{arm_a['tag']}_Opt1" if arm_a["end"] == "L" else f"{arm_a['tag']}_Opt4"
                    p_b = f"{arm_b['tag']}_Opt2" if arm_b["end"] == "L" else f"{arm_b['tag']}_Opt3"
                    link(p_a, p_b)

        all_possible_ports = set()
        for tag in self.mzi_data:
            for p in ["Opt1", "Opt2", "Opt3", "Opt4"]:
                all_possible_ports.add(f"{tag}_{p}")

        open_ports = all_possible_ports - connected_ports
        self.graph = PhotonicMeshGraph(self.mzi_data, connections, list(open_ports))
        return open_ports, connections

    def get_free_boundary_ports(self):
        open_ports, _ = self._build_topology_connections()
        return sorted(list(open_ports))

    def _build_main_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=590)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(self, corner_radius=10)
        self.frame_left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self._setup_matplotlib_view()

        self.frame_right = ctk.CTkFrame(self, corner_radius=10, width=590)
        self.frame_right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.frame_right.grid_propagate(False)

        self.tabview = ctk.CTkTabview(self.frame_right)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.tab_home = self.tabview.add("Home")
        self.tab_tbu = self.tabview.add("TBU_settings")
        self.tab_tuning = self.tabview.add("Mesh_tuning")
        self.tab_ports = self.tabview.add("Port_settings")
        self.tab_inspect = self.tabview.add("Port_Inspect")
        self.tab_router = self.tabview.add("Router")
        self.tab_matrix = self.tabview.add("Matrix_Compiler")

        self._build_home_tab()
        self._build_tbu_tab()
        self._build_tuning_tab()
        self._build_ports_tab()
        self._build_inspect_tab()
        self._build_router_tab()
        self._build_matrix_tab()
        
        # Populate all dropdowns ONLY AFTER all tabs are fully built
        self._refresh_router_port_dropdowns()

    # -------------------------------------------------------------
    # Matplotlib Canvas
    # -------------------------------------------------------------
    def _setup_matplotlib_view(self):
        self.fig, self.ax = plt.subplots(figsize=(8, 8), facecolor="#1e1e1e")
        self.ax.set_facecolor("#1e1e1e")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_left)
        self.canvas.draw()

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.frame_left)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Create the dynamic hover tooltip (hidden initially)
        self.tooltip = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, -15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#2C3E50", ec="#00FFCC", alpha=0.9, lw=1.5),
            color="white",
            fontfamily="Consolas",
            fontsize=9,
            zorder=30,
            ha="left",
            va="top"
        )
        self.tooltip.set_visible(False)
        self.hovered_item = None

        self._render_mesh_canvas()
        self.fig.canvas.mpl_connect("pick_event", self._on_pick)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _render_mesh_canvas(self):
        self.ax.clear()
        
        # Re-add the tooltip to the cleared axes
        self.tooltip = self.ax.annotate(
            "", xy=(0, 0), xytext=(15, -15), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#2C3E50", ec="#00FFCC", alpha=0.9, lw=1.5),
            color="white", fontfamily="Consolas", fontsize=9, zorder=30, ha="left", va="top"
        )
        self.tooltip.set_visible(False)

        self.patches_dict.clear()
        self.port_artists.clear()
        self.port_coords.clear()
        
        self.active_route_lines.clear()
        self.alt_route_lines.clear()
        self.matrix_route_lines.clear()
        
        self.selected_port_circle = None
        self.src_highlight_circle = None
        self.dst_highlight_circle = None

        self.open_ports_set, self.port_connections = self._build_topology_connections()

        for m in range(1, self.num_cols + 1):
            y_offset_col = (m % 2) * (self.dy / 2.0)
            for n in range(1, self.num_rows + 1):
                v_x = (m - 1) * self.dx
                v_y = -(n - 1) * self.dy - y_offset_col

                self._draw_mzi_patch(v_x - (self.arm_span / 2.0), v_y, 0, f"MZI_{m}_{n}_in")
                self._draw_mzi_patch(
                    v_x + (self.arm_span / 2.0) * self.cos60,
                    v_y + (self.arm_span / 2.0) * self.sin60,
                    60,
                    f"MZI_{m}_{n}_up",
                )
                self._draw_mzi_patch(
                    v_x + (self.arm_span / 2.0) * self.cos60,
                    v_y - (self.arm_span / 2.0) * self.sin60,
                    -60,
                    f"MZI_{m}_{n}_down",
                )

                box = patches.Rectangle(
                    (v_x - self.arm_span, v_y - self.dy / 2.0),
                    self.arm_span * (1 + self.cos60),
                    self.dy,
                    linewidth=0.8,
                    edgecolor="#555555",
                    facecolor="none",
                    linestyle="--",
                    alpha=0.4,
                    zorder=1,
                )
                self.ax.add_patch(box)

        self.ax.set_aspect("equal", "box")
        self.ax.autoscale_view()
        self.ax.axis("off")
        self.canvas.draw_idle()

    def _draw_mzi_patch(self, center_x, center_y, rot_deg, tag):
        data = self.mzi_data[tag]
        state_cfg = STATE_CONFIGS.get(data["state"], STATE_CONFIGS["AV"])

        rect = patches.Rectangle(
            (-self.L / 2.0, -self.w / 2.0),
            self.L,
            self.w,
            facecolor=state_cfg["color"],
            edgecolor=state_cfg["edge"],
            lw=1.2,
            zorder=3,
        )
        t = (
            patches.transforms.Affine2D().rotate_deg(rot_deg)
            + patches.transforms.Affine2D().translate(center_x, center_y)
            + self.ax.transData
        )
        rect.set_transform(t)
        rect.set_picker(True)
        rect.tag = tag
        rect.artist_type = "MZI"

        self.ax.add_patch(rect)
        self.patches_dict[tag] = rect

        self.ax.text(
            center_x,
            center_y,
            tag,
            color="white" if "DEF_" in data["state"] else "black",
            fontsize=6,
            ha="center",
            va="center",
            weight="bold",
            rotation=rot_deg if rot_deg != 0 else 0,
            zorder=5,
        )

        rad = np.deg2rad(rot_deg)
        cos_r, sin_r = np.cos(rad), np.sin(rad)
        perp_x, perp_y = -sin_r, cos_r
        dir_x, dir_y = cos_r, sin_r

        port_offsets = {
            "Opt1": (-1, self.port_sep / 2.0),
            "Opt2": (-1, -self.port_sep / 2.0),
            "Opt3": (1, self.port_sep / 2.0),
            "Opt4": (1, -self.port_sep / 2.0),
        }

        lead_span = self.port_len

        for pname, (side, offset) in port_offsets.items():
            px = center_x + side * (self.L / 2.0) * dir_x + offset * perp_x
            py = center_y + side * (self.L / 2.0) * dir_y + offset * perp_y
            end_x = px + side * lead_span * dir_x
            end_y = py + side * lead_span * dir_y

            port_id = f"{tag}_{pname}"
            self.port_coords[port_id] = (end_x, end_y)
            is_open = port_id in self.open_ports_set

            color = "#00FF66" if is_open else "#777777"
            lw = 2.2 if is_open else 1.2
            zorder = 4 if is_open else 2

            self.ax.plot([px, end_x], [py, end_y], color=color, lw=lw, zorder=zorder)

            circle_color = "#00FF66" if is_open else "#3498DB"
            port_circle = patches.Circle(
                (end_x, end_y),
                radius=0.05,
                facecolor=circle_color,
                edgecolor="#FFFFFF",
                lw=0.6,
                picker=5,
                zorder=6,
            )
            port_circle.port_id = port_id
            port_circle.artist_type = "PORT"
            self.ax.add_patch(port_circle)
            self.port_artists[port_id] = port_circle

    def _on_hover(self, event):
        """Dynamically displays tooltips when hovering over MZIs or Ports."""
        if event.inaxes != self.ax:
            if self.tooltip.get_visible():
                self.tooltip.set_visible(False)
                self.hovered_item = None
                self.canvas.draw_idle()
            return

        hovered_now = None
        hover_text = ""

        # 1. Check Ports First (Since they are small and drawn on top)
        for port_id, artist in self.port_artists.items():
            contains, _ = artist.contains(event)
            if contains:
                hovered_now = port_id
                partner = self.port_connections.get(port_id, "OPEN BOUNDARY / I-O")
                hover_text = f"🔹 PORT: {port_id}\n🔗 LINK: {partner}"
                break

        # 2. Check MZIs if no port is hovered
        if not hovered_now:
            for mzi_tag, artist in self.patches_dict.items():
                contains, _ = artist.contains(event)
                if contains:
                    hovered_now = mzi_tag
                    d = self.mzi_data.get(mzi_tag, {})
                    st = d.get("state", "AV")
                    tph = d.get("tpH_v", 0.0)
                    bth = d.get("btH_v", 0.0)
                    hover_text = f"⬛ TBU: {mzi_tag}\n⚙️ STATE: {st}\n⚡ tpH: {tph:.2f}V\n⚡ btH: {bth:.2f}V"
                    break

        # Only update and redraw if the hovered item CHANGED (prevents lag)
        if hovered_now != self.hovered_item:
            self.hovered_item = hovered_now
            if hovered_now:
                self.tooltip.set_text(hover_text)
                self.tooltip.xy = (event.xdata, event.ydata)
                self.tooltip.set_visible(True)
            else:
                self.tooltip.set_visible(False)
            self.canvas.draw_idle()

    def _cycle_defect_state(self, tag):
        """Cycles an MZI through various stuck-fault physical defect states on right-click."""
        current = self.mzi_data[tag].get("state", "AV")
        defect_cycle = ["AV", "DEF_BS", "DEF_CS", "DEF_DEAD"]
        
        if current in defect_cycle:
            next_idx = (defect_cycle.index(current) + 1) % len(defect_cycle)
            new_state = defect_cycle[next_idx]
        else:
            new_state = "DEF_BS" # Start cycle if currently normal
        
        self.mzi_data[tag]["state"] = new_state
        cfg = STATE_CONFIGS[new_state]
        self.mzi_data[tag]["tpH_v"] = cfg["tpH_v"]
        self.mzi_data[tag]["tpH_p"] = cfg["tpH_p"]
        self.mzi_data[tag]["btH_v"] = cfg["btH_v"]
        self.mzi_data[tag]["btH_p"] = cfg["btH_p"]
        
        self.patches_dict[tag].set_facecolor(cfg["color"])
        # Change text color to white for better readability on dark defect blocks
        for t in self.ax.texts:
            if t.get_text() == tag:
                t.set_color("white" if "DEF_" in new_state else "black")

        self.is_modified = True
        self._build_topology_connections()
        self._sync_tbu_tab()
        self._populate_port_table()
        self._update_home_metrics()
        self.canvas.draw_idle()

    def _on_pick(self, event):
        artist = event.artist
        artist_type = getattr(artist, "artist_type", None)

        if artist_type == "PORT":
            port_id = getattr(artist, "port_id", None)
            if not port_id:
                return

            if self.picking_target == "SRC":
                if hasattr(self, 'cmb_route_src'): self.cmb_route_src.set(port_id)
                self._update_router_port_marker("SRC", port_id)
                self._set_picking_mode(None)
                return
            elif self.picking_target == "DST":
                if hasattr(self, 'cmb_route_dst'): self.cmb_route_dst.set(port_id)
                self._update_router_port_marker("DST", port_id)
                self._set_picking_mode(None)
                return
            elif self.picking_target == "MATRIX_SRC":
                if hasattr(self, 'cmb_matrix_src'): self.cmb_matrix_src.set(port_id)
                self._update_router_port_marker("SRC", port_id) 
                self._set_picking_mode(None)
                return
            elif self.picking_target == "MATRIX_DST":
                if hasattr(self, 'cmb_matrix_dst'): self.cmb_matrix_dst.set(port_id)
                self._update_router_port_marker("DST", port_id) 
                self._set_picking_mode(None)
                return

            self._inspect_port(port_id)

        elif artist_type == "MZI":
            tag = getattr(artist, "tag", None)
            if tag:
                # Right Click (Button 3) triggers fault simulation
                if event.mouseevent.button == 3:
                    self._cycle_defect_state(tag)
                else:
                    self._select_mzi(tag)

    def _update_router_port_marker(self, target_type, port_id):
        if port_id not in self.port_coords:
            return
        cx, cy = self.port_coords[port_id]

        if target_type == "SRC":
            if self.src_highlight_circle:
                try:
                    self.src_highlight_circle.remove()
                except Exception:
                    pass
            self.src_highlight_circle = patches.Circle(
                (cx, cy), radius=0.09, fill=False, edgecolor="#00FFFF", lw=2.5, zorder=8
            )
            self.ax.add_patch(self.src_highlight_circle)

        elif target_type == "DST":
            if self.dst_highlight_circle:
                try:
                    self.dst_highlight_circle.remove()
                except Exception:
                    pass
            self.dst_highlight_circle = patches.Circle(
                (cx, cy), radius=0.09, fill=False, edgecolor="#FF00FF", lw=2.5, zorder=8
            )
            self.ax.add_patch(self.dst_highlight_circle)

        self.canvas.draw_idle()

    def _inspect_port(self, port_id):
        is_open = port_id in self.open_ports_set
        partner = self.port_connections.get(port_id, None)

        if self.selected_port_circle:
            try:
                self.selected_port_circle.remove()
            except Exception:
                pass

        if port_id in self.port_artists:
            p_circ = self.port_artists[port_id]
            cx, cy = p_circ.center
            self.selected_port_circle = patches.Circle(
                (cx, cy), radius=0.08, fill=False, edgecolor="#FF9900", lw=2.2, zorder=7
            )
            self.ax.add_patch(self.selected_port_circle)
            self.canvas.draw_idle()

        parent_mzi = port_id.rsplit("_", 1)[0]
        port_name = port_id.rsplit("_", 1)[1]

        edges_from_node = self.graph.adjacency_list.get(port_id, [])
        edges_str = "\n".join([
            f"  ➔ Edge to [{e['target']}] | Mode: {e['type']} | Transmission: {e['weight']}"
            for e in edges_from_node
        ])

        self.lbl_inspect_title.configure(text=f"Graph Vertex: {port_id}")
        self.lbl_inspect_parent.configure(text=f"Parent TBU: {parent_mzi}")
        self.lbl_inspect_pname.configure(text=f"Optical Identifier: {port_name}")

        if is_open:
            self.lbl_inspect_status.configure(
                text="GRAPH STATUS: 🟢 OPEN I/O NODE (External Port)", text_color="#00FF66"
            )
            self.lbl_inspect_detail.configure(
                text=f"External Laser / Detector Interface.\n\nOutgoing Graph Transitions:\n{edges_str if edges_str else '  None'}"
            )
            self.btn_inspect_partner.configure(state="disabled", text="No Inter-TBU Partner")
        else:
            partner_mzi = partner.rsplit("_", 1)[0]
            partner_port = partner.rsplit("_", 1)[1]

            self.lbl_inspect_status.configure(
                text="GRAPH STATUS: 🔗 INTERNAL WAVEGUIDE VERTEX", text_color="#3498DB"
            )
            self.lbl_inspect_detail.configure(
                text=f"Waveguide Partner: {partner_mzi} [{partner_port}]\n\nOutgoing Graph Transitions:\n{edges_str if edges_str else '  None'}"
            )
            self.btn_inspect_partner.configure(
                state="normal",
                text=f"Select Partner ({partner_mzi})",
                command=lambda: self._select_mzi(partner_mzi),
            )

        self.tabview.set("Port_Inspect")

    def _select_mzi(self, tag):
        if tag not in self.mzi_data:
            return
        if self.selected_mzi and self.selected_mzi in self.patches_dict:
            old_state = self.mzi_data[self.selected_mzi]["state"]
            self.patches_dict[self.selected_mzi].set_edgecolor(
                STATE_CONFIGS.get(old_state, STATE_CONFIGS["AV"])["edge"]
            )
            self.patches_dict[self.selected_mzi].set_linewidth(1.2)

        self.selected_mzi = tag
        self.patches_dict[tag].set_edgecolor("#00FFCC")
        self.patches_dict[tag].set_linewidth(2.5)
        self.canvas.draw_idle()

        self._sync_tbu_tab()
        self._sync_ports_tab()
        self._update_home_metrics()

    # -------------------------------------------------------------
    # TAB 1: HOME
    # -------------------------------------------------------------
    def _build_home_tab(self):
        lbl_title = ctk.CTkLabel(
            self.tab_home, text="Photonic Mesh Dashboard", font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(anchor="w", padx=10, pady=(10, 5))

        io_frame = ctk.CTkFrame(self.tab_home)
        io_frame.pack(fill="x", padx=10, pady=5)

        btn_save = ctk.CTkButton(
            io_frame,
            text="💾 Export Lumerical JSON",
            command=self._save_json,
            fg_color="#1E8449",
            hover_color="#145A32",
        )
        btn_save.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        btn_load = ctk.CTkButton(
            io_frame,
            text="📂 Load Mesh JSON",
            command=self._load_json,
            fg_color="#2E86C1",
            hover_color="#1B4F72",
        )
        btn_load.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        io_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_home_info = ctk.CTkLabel(
            self.tab_home, text="TIP: Right-Click an MZI on the canvas to cycle Hardware Defect states.\n", justify="left", font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.lbl_home_info.pack(anchor="w", padx=10, pady=10)

        legend_frame = ctk.CTkFrame(self.tab_home)
        legend_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(legend_frame, text="State Legend:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        for i, (k, v) in enumerate(STATE_CONFIGS.items(), start=1):
            lbl_box = tk.Label(legend_frame, text="    ", bg=v["color"])
            lbl_box.grid(row=i, column=0, padx=10, pady=2, sticky="w")
            ctk.CTkLabel(legend_frame, text=f"{v['label']} - {v['desc']}").grid(
                row=i, column=1, padx=5, pady=2, sticky="w"
            )

    def _update_home_metrics(self):
        total_tbus = len(self.mzi_data)
        counts = {"BS": 0, "CS": 0, "TC": 0, "AV": 0, "DEF_BS": 0, "DEF_CS": 0, "DEF_DEAD": 0}
        for d in self.mzi_data.values():
            counts[d.get("state", "AV")] = counts.get(d.get("state", "AV"), 0) + 1

        summary = (
            f"Grid Configuration:  {self.num_cols} x {self.num_rows} (Honeycomb Lattice)\n"
            f"Total TBUs/MZIs:     {total_tbus}\n"
            f"Graph Total Vertices:{len(self.mzi_data) * 4}\n"
            f"Open I/O Graph Nodes:{len(self.get_free_boundary_ports())}\n"
            f"--------------------------------------------------\n"
            f"• Bar States (BS):        {counts['BS']}\n"
            f"• Cross States (CS):      {counts['CS']}\n"
            f"• Tunable Couplers (TC):  {counts['TC']}\n"
            f"• Available / Idle (AV):  {counts['AV']}\n"
            f"• Defective / Faulty:     {counts['DEF_BS']+counts['DEF_CS']+counts['DEF_DEAD']}\n"
            f"--------------------------------------------------\n"
            f"Active Unit: {self.selected_mzi}\n\n"
            f"TIP: Right-Click an MZI to simulate Hardware Defects."
        )
        self.lbl_home_info.configure(text=summary)

    def _save_json(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Export Mesh & Graph Configuration",
        )
        if not file_path:
            return False

        open_ports, connections = self._build_topology_connections()

        tbus_export = {}
        for tag, d in self.mzi_data.items():
            tbus_export[tag] = {
                **d,
                "optical_ports": {
                    "Opt1": f"{tag}_Opt1",
                    "Opt2": f"{tag}_Opt2",
                    "Opt3": f"{tag}_Opt3",
                    "Opt4": f"{tag}_Opt4",
                },
                "open_ports": [
                    f"{tag}_{p}"
                    for p in ["Opt1", "Opt2", "Opt3", "Opt4"]
                    if f"{tag}_{p}" in open_ports
                ],
                "port_connections": {
                    f"{tag}_{p}": connections.get(f"{tag}_{p}", "OPEN")
                    for p in ["Opt1", "Opt2", "Opt3", "Opt4"]
                },
            }

        export_data = {
            "metadata": {
                "format": "FPPGA_Hexagonal_Mesh",
                "version": "3.0",
                "target": "Lumerical_INTERCONNECT",
                "V_PI": V_PI,
            },
            "grid": {
                "num_cols": self.num_cols,
                "num_rows": self.num_rows,
                "L_um": self.L,
                "w_um": self.w,
                "port_len_um": self.port_len,
                "port_sep_um": self.port_sep,
                "node_gap_um": self.node_gap,
            },
            "mesh_summary": {
                "total_tbus": len(self.mzi_data),
                "total_open_ports": len(open_ports),
                "free_optical_ports": sorted(list(open_ports)),
            },
            "graph_representation": self.graph.export_graph_json(),
            "tbus": tbus_export,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4)
            self.is_modified = False
            messagebox.showinfo("Success", f"Configuration & Graph exported to:\n{file_path}")
            return True
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not write file:\n{e}")
            return False

    def _load_json(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Mesh Configuration JSON",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)

            grid = imported_data.get("grid", {})
            self.num_cols = int(grid.get("num_cols", self.num_cols))
            self.num_rows = int(grid.get("num_rows", self.num_rows))
            self.L = float(grid.get("L_um", self.L))
            self.w = float(grid.get("w_um", self.w))
            self.port_len = float(grid.get("port_len_um", self.port_len))
            self.port_sep = float(grid.get("port_sep_um", self.port_sep))
            self.node_gap = float(grid.get("node_gap_um", self.node_gap))

            self._update_geometry_math()

            self.ent_mesh_m.delete(0, tk.END)
            self.ent_mesh_m.insert(0, str(self.num_cols))
            self.ent_mesh_n.delete(0, tk.END)
            self.ent_mesh_n.insert(0, str(self.num_rows))
            self.ent_mzi_l.delete(0, tk.END)
            self.ent_mzi_l.insert(0, str(self.L))
            self.ent_mzi_w.delete(0, tk.END)
            self.ent_mzi_w.insert(0, str(self.w))
            self.ent_port_len.delete(0, tk.END)
            self.ent_port_len.insert(0, str(self.port_len))
            self.ent_port_sep.delete(0, tk.END)
            self.ent_port_sep.insert(0, str(self.port_sep))
            self.ent_node_gap.delete(0, tk.END)
            self.ent_node_gap.insert(0, str(self.node_gap))

            self.mzi_data = imported_data.get("tbus", {})

            self._render_mesh_canvas()
            first_key = next(iter(self.mzi_data.keys()), "MZI_1_1_in")
            self._select_mzi(first_key)
            self._populate_port_table()
            self._update_home_metrics()
            self._refresh_router_port_dropdowns()
            self.is_modified = False

            messagebox.showinfo("Success", "Configuration successfully imported.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to load JSON mesh:\n{e}")

    # -------------------------------------------------------------
    # TAB 2: TBU_SETTINGS
    # -------------------------------------------------------------
    def _build_tbu_tab(self):
        self.lbl_tbu_title = ctk.CTkLabel(
            self.tab_tbu, text="TBU: None", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_tbu_title.pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(self.tab_tbu, text="Operating State Preset:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(5, 2)
        )
        self.tbu_state_var = tk.StringVar(value="AV")

        for code, cfg in STATE_CONFIGS.items():
            r = ctk.CTkRadioButton(
                self.tab_tbu,
                text=cfg["label"],
                value=code,
                variable=self.tbu_state_var,
                command=self._on_state_selected,
            )
            r.pack(anchor="w", padx=20, pady=3)

        ctk.CTkLabel(self.tab_tbu, text="Top Phase Shifter [tpH]:", font=ctk.CTkFont(weight="bold", size=13)).pack(
            anchor="w", padx=10, pady=(15, 2)
        )
        frame_tph = ctk.CTkFrame(self.tab_tbu)
        frame_tph.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_tph, text="Voltage (V):").grid(row=0, column=0, padx=5, pady=5)
        self.ent_tph_v = ctk.CTkEntry(frame_tph, width=80)
        self.ent_tph_v.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_tph, text="Phase (rad):").grid(row=0, column=2, padx=5, pady=5)
        self.ent_tph_p = ctk.CTkEntry(frame_tph, width=80)
        self.ent_tph_p.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(
            self.tab_tbu, text="Bottom Phase Shifter [btH]:", font=ctk.CTkFont(weight="bold", size=13)
        ).pack(anchor="w", padx=10, pady=(15, 2))
        frame_bth = ctk.CTkFrame(self.tab_tbu)
        frame_bth.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_bth, text="Voltage (V):").grid(row=0, column=0, padx=5, pady=5)
        self.ent_bth_v = ctk.CTkEntry(frame_bth, width=80)
        self.ent_bth_v.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_bth, text="Phase (rad):").grid(row=0, column=2, padx=5, pady=5)
        self.ent_bth_p = ctk.CTkEntry(frame_bth, width=80)
        self.ent_bth_p.grid(row=0, column=3, padx=5, pady=5)

        btn_apply = ctk.CTkButton(
            self.tab_tbu, text="Apply Custom Voltages/Phases", command=self._apply_custom_tbu_values
        )
        btn_apply.pack(padx=10, pady=15)

    def _sync_tbu_tab(self):
        if not self.selected_mzi or self.selected_mzi not in self.mzi_data:
            return
        d = self.mzi_data[self.selected_mzi]
        self.lbl_tbu_title.configure(text=f"TBU Target: {self.selected_mzi}")
        self.tbu_state_var.set(d.get("state", "AV"))

        self.ent_tph_v.delete(0, tk.END)
        self.ent_tph_v.insert(0, f"{d['tpH_v']:.3f}")
        self.ent_tph_p.delete(0, tk.END)
        self.ent_tph_p.insert(0, f"{d['tpH_p']:.3f}")

        self.ent_bth_v.delete(0, tk.END)
        self.ent_bth_v.insert(0, f"{d['btH_v']:.3f}")
        self.ent_bth_p.delete(0, tk.END)
        self.ent_bth_p.insert(0, f"{d['btH_p']:.3f}")

    def _on_state_selected(self):
        if not self.selected_mzi:
            return
        code = self.tbu_state_var.get()
        cfg = STATE_CONFIGS[code]

        d = self.mzi_data[self.selected_mzi]
        d["state"] = code
        d["tpH_v"] = cfg["tpH_v"]
        d["tpH_p"] = cfg["tpH_p"]
        d["btH_v"] = cfg["btH_v"]
        d["btH_p"] = cfg["btH_p"]

        self.is_modified = True

        patch = self.patches_dict[self.selected_mzi]
        patch.set_facecolor(cfg["color"])
        # Change text color to white for better readability on dark defect blocks
        for t in self.ax.texts:
            if t.get_text() == self.selected_mzi:
                t.set_color("white" if "DEF_" in code else "black")

        self._build_topology_connections()
        self._sync_tbu_tab()
        self._update_home_metrics()
        self.canvas.draw_idle()

    def _apply_custom_tbu_values(self):
        if not self.selected_mzi:
            return
        try:
            tph_v = float(self.ent_tph_v.get())
            tph_p = float(self.ent_tph_p.get())
            bth_v = float(self.ent_bth_v.get())
            bth_p = float(self.ent_bth_p.get())

            d = self.mzi_data[self.selected_mzi]
            d["tpH_v"] = tph_v
            d["tpH_p"] = tph_p
            d["btH_v"] = bth_v
            d["btH_p"] = bth_p

            self.is_modified = True
            self._build_topology_connections()
            messagebox.showinfo("Success", f"Values successfully applied to {self.selected_mzi}")
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values entered.")

    # -------------------------------------------------------------
    # TAB 3: MESH_TUNING
    # -------------------------------------------------------------
    def _build_tuning_tab(self):
        ctk.CTkLabel(
            self.tab_tuning, text="Mesh Dimension Tuning", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        frame_dim = ctk.CTkFrame(self.tab_tuning)
        frame_dim.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_dim, text="Columns (m):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.ent_mesh_m = ctk.CTkEntry(frame_dim, width=65)
        self.ent_mesh_m.insert(0, str(self.num_cols))
        self.ent_mesh_m.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="Rows (n):").grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.ent_mesh_n = ctk.CTkEntry(frame_dim, width=65)
        self.ent_mesh_n.insert(0, str(self.num_rows))
        self.ent_mesh_n.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="MZI Length (L):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.ent_mzi_l = ctk.CTkEntry(frame_dim, width=65)
        self.ent_mzi_l.insert(0, str(self.L))
        self.ent_mzi_l.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="MZI Width (w):").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.ent_mzi_w = ctk.CTkEntry(frame_dim, width=65)
        self.ent_mzi_w.insert(0, str(self.w))
        self.ent_mzi_w.grid(row=1, column=3, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="Port Arm Len:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.ent_port_len = ctk.CTkEntry(frame_dim, width=65)
        self.ent_port_len.insert(0, str(self.port_len))
        self.ent_port_len.grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="Port Pitch:").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.ent_port_sep = ctk.CTkEntry(frame_dim, width=65)
        self.ent_port_sep.insert(0, str(self.port_sep))
        self.ent_port_sep.grid(row=2, column=3, padx=5, pady=5)

        ctk.CTkLabel(frame_dim, text="Node Center Gap:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.ent_node_gap = ctk.CTkEntry(frame_dim, width=65)
        self.ent_node_gap.insert(0, str(self.node_gap))
        self.ent_node_gap.grid(row=3, column=1, padx=5, pady=5)

        btn_resize = ctk.CTkButton(self.tab_tuning, text="Re-generate Mesh Grid", command=self._rebuild_grid)
        btn_resize.pack(padx=10, pady=10)

        ctk.CTkLabel(self.tab_tuning, text="Batch State Configuration:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(20, 5)
        )
        frame_batch = ctk.CTkFrame(self.tab_tuning)
        frame_batch.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(frame_batch, text="Set ALL to BS", command=lambda: self._batch_set_state("BS")).grid(
            row=0, column=0, padx=5, pady=5
        )
        ctk.CTkButton(frame_batch, text="Set ALL to CS", command=lambda: self._batch_set_state("CS")).grid(
            row=0, column=1, padx=5, pady=5
        )
        ctk.CTkButton(frame_batch, text="Set ALL to TC", command=lambda: self._batch_set_state("TC")).grid(
            row=1, column=0, padx=5, pady=5
        )
        ctk.CTkButton(frame_batch, text="Reset ALL (AV)", command=lambda: self._batch_set_state("AV")).grid(
            row=1, column=1, padx=5, pady=5
        )

    def _rebuild_grid(self):
        try:
            m = int(self.ent_mesh_m.get())
            n = int(self.ent_mesh_n.get())
            l_val = float(self.ent_mzi_l.get())
            w_val = float(self.ent_mzi_w.get())
            p_len = float(self.ent_port_len.get())
            p_sep = float(self.ent_port_sep.get())
            n_gap = float(self.ent_node_gap.get())

            if m < 1 or n < 1 or m > 10 or n > 10:
                raise ValueError("Grid columns and rows must be between 1 and 10.")
            if l_val <= 0 or w_val <= 0 or p_len <= 0 or p_sep <= 0 or n_gap < 0:
                raise ValueError("Dimensions must be positive values (Node gap >= 0).")

            self.num_cols = m
            self.num_rows = n
            self.L = l_val
            self.w = w_val
            self.port_len = p_len
            self.port_sep = p_sep
            self.node_gap = n_gap

            self._update_geometry_math()
            self._init_mesh_data()
            self.is_modified = True
            self._render_mesh_canvas()
            self._select_mzi("MZI_1_1_in")
            self._populate_port_table()
            self._refresh_router_port_dropdowns()
        except ValueError as e:
            messagebox.showerror("Invalid Parameters", f"{e}")

    def _batch_set_state(self, state_code):
        cfg = STATE_CONFIGS[state_code]
        for tag in self.mzi_data:
            if self.mzi_data[tag]["state"].startswith("DEF_"):
                continue # Do NOT overwrite physical defects with batch logical changes
                
            self.mzi_data[tag]["state"] = state_code
            self.mzi_data[tag]["tpH_v"] = cfg["tpH_v"]
            self.mzi_data[tag]["tpH_p"] = cfg["tpH_p"]
            self.mzi_data[tag]["btH_v"] = cfg["btH_v"]
            self.mzi_data[tag]["btH_p"] = cfg["btH_p"]
            self.patches_dict[tag].set_facecolor(cfg["color"])

        self.is_modified = True
        self._build_topology_connections()
        self._sync_tbu_tab()
        self._populate_port_table()
        self._update_home_metrics()
        self.canvas.draw_idle()

    # -------------------------------------------------------------
    # TAB 4: PORT_SETTINGS
    # -------------------------------------------------------------
    def _build_ports_tab(self):
        ctk.CTkLabel(
            self.tab_ports, text="TBU Ports & Routing Directory", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.tree_frame = ctk.CTkFrame(self.tab_ports)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("sno", "tbu", "status", "port_tph", "tph_v", "port_bth", "bth_v", "open_ports")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=15)

        self.tree.heading("sno", text="S.No")
        self.tree.heading("tbu", text="TBU Name")
        self.tree.heading("status", text="State")
        self.tree.heading("port_tph", text="Top Port (tpH)")
        self.tree.heading("tph_v", text="tpH (V)")
        self.tree.heading("port_bth", text="Bottom Port (btH)")
        self.tree.heading("bth_v", text="btH (V)")
        self.tree.heading("open_ports", text="Boundary Open Ports")

        self.tree.column("sno", width=45, anchor="center")
        self.tree.column("tbu", width=95)
        self.tree.column("status", width=55)
        self.tree.column("port_tph", width=115)
        self.tree.column("tph_v", width=55)
        self.tree.column("port_bth", width=115)
        self.tree.column("bth_v", width=55)
        self.tree.column("open_ports", width=160)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._on_table_row_double_click)
        self._populate_port_table()

    def _populate_port_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        open_ports, _ = self._build_topology_connections()

        for idx, (tag, d) in enumerate(self.mzi_data.items(), start=1):
            open_p = [p for p in ["Opt1", "Opt2", "Opt3", "Opt4"] if f"{tag}_{p}" in open_ports]
            self.tree.insert(
                "",
                "end",
                values=(
                    idx,
                    tag,
                    d.get("state", "AV"),
                    d.get("tpH_pin", ""),
                    f"{d.get('tpH_v', 0.0):.2f}",
                    d.get("btH_pin", ""),
                    f"{d.get('btH_v', 0.0):.2f}",
                    ", ".join(open_p) if open_p else "All Connected",
                ),
            )

    def _on_table_row_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        row_vals = self.tree.item(item, "values")
        if row_vals and len(row_vals) > 1:
            tbu_tag = row_vals[1]
            self._select_mzi(tbu_tag)
            self.tabview.set("TBU_settings")

    def _sync_ports_tab(self):
        self._populate_port_table()

    # -------------------------------------------------------------
    # TAB 5: PORT_INSPECT
    # -------------------------------------------------------------
    def _build_inspect_tab(self):
        lbl_head = ctk.CTkLabel(
            self.tab_inspect, text="Optical Port Inspection Terminal", font=ctk.CTkFont(size=17, weight="bold")
        )
        lbl_head.pack(anchor="w", padx=10, pady=(10, 10))

        card_info = ctk.CTkFrame(self.tab_inspect, corner_radius=8)
        card_info.pack(fill="x", padx=10, pady=5)

        self.lbl_inspect_title = ctk.CTkLabel(
            card_info,
            text="Selected Port: None (Click any dot on canvas)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00FFCC",
        )
        self.lbl_inspect_title.pack(anchor="w", padx=15, pady=(12, 4))

        self.lbl_inspect_parent = ctk.CTkLabel(card_info, text="Parent TBU: -", font=ctk.CTkFont(size=13))
        self.lbl_inspect_parent.pack(anchor="w", padx=15, pady=2)

        self.lbl_inspect_pname = ctk.CTkLabel(card_info, text="Optical Identifier: -", font=ctk.CTkFont(size=13))
        self.lbl_inspect_pname.pack(anchor="w", padx=15, pady=2)

        self.lbl_inspect_status = ctk.CTkLabel(card_info, text="STATUS: -", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_inspect_status.pack(anchor="w", padx=15, pady=(4, 12))

        card_routing = ctk.CTkFrame(self.tab_inspect, corner_radius=8)
        card_routing.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            card_routing, text="Routing & Netlist Linkage:", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.lbl_inspect_detail = ctk.CTkLabel(
            card_routing,
            text="Click any optical port circle on the hexagonal mesh canvas to inspect its waveguide route.",
            justify="left",
            wraplength=480,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.lbl_inspect_detail.pack(anchor="w", padx=15, pady=5)

        self.btn_inspect_partner = ctk.CTkButton(
            card_routing,
            text="No Connected Neighbor",
            state="disabled",
            fg_color="#3498DB",
            hover_color="#2980B9",
        )
        self.btn_inspect_partner.pack(padx=15, pady=(15, 10), fill="x")

    # -------------------------------------------------------------
    # TAB 6: OPTICAL ROUTER (Multipath Finder & Shared states)
    # -------------------------------------------------------------
    def _build_router_tab(self):
        lbl_head = ctk.CTkLabel(
            self.tab_router, text="Multipath Optical Router", font=ctk.CTkFont(size=17, weight="bold")
        )
        lbl_head.pack(anchor="w", padx=10, pady=(10, 10))

        frame_sel = ctk.CTkFrame(self.tab_router, corner_radius=8)
        frame_sel.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_sel, text="Source Port:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 2), sticky="w"
        )
        self.cmb_route_src = ctk.CTkComboBox(frame_sel, width=200, values=[], command=self._on_src_combo_change)
        self.cmb_route_src.grid(row=0, column=1, padx=5, pady=(10, 2), sticky="ew")

        self.btn_pick_src = ctk.CTkButton(
            frame_sel,
            text="📌 Pick from Mesh Canvas",
            width=140,
            command=lambda: self._set_picking_mode("SRC"),
            fg_color="#34495E",
            hover_color="#1A5276",
        )
        self.btn_pick_src.grid(row=0, column=2, padx=10, pady=(10, 2))

        ctk.CTkLabel(frame_sel, text="Dest Port:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=10, pady=(5, 10), sticky="w"
        )
        self.cmb_route_dst = ctk.CTkComboBox(frame_sel, width=200, values=[], command=self._on_dst_combo_change)
        self.cmb_route_dst.grid(row=1, column=1, padx=5, pady=(5, 10), sticky="ew")

        self.btn_pick_dst = ctk.CTkButton(
            frame_sel,
            text="📌 Pick from Mesh Canvas",
            width=140,
            command=lambda: self._set_picking_mode("DST"),
            fg_color="#34495E",
            hover_color="#1A5276",
        )
        self.btn_pick_dst.grid(row=1, column=2, padx=10, pady=(5, 10))

        frame_sel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_router, text="Routing Constraint Strategy:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 2)
        )
        self.router_mode_var = tk.StringVar(value="SHARED")

        rb_av = ctk.CTkRadioButton(self.tab_router, text="Strictly Available / Idle MZIs Only", value="AV_ONLY", variable=self.router_mode_var)
        rb_av.pack(anchor="w", padx=25, pady=3)

        rb_shared = ctk.CTkRadioButton(self.tab_router, text="Shared Non-Conflicting (Allow Cross/Bar Multipath)", value="SHARED", variable=self.router_mode_var)
        rb_shared.pack(anchor="w", padx=25, pady=3)

        rb_any = ctk.CTkRadioButton(self.tab_router, text="Any Mesh Path (Overwrite existing routing)", value="ANY", variable=self.router_mode_var)
        rb_any.pack(anchor="w", padx=25, pady=3)

        btn_frame = ctk.CTkFrame(self.tab_router)
        btn_frame.pack(fill="x", padx=10, pady=10)

        btn_find = ctk.CTkButton(
            btn_frame, text="⚡ Compute Multipaths", command=self._compute_and_display_route, fg_color="#D35400", hover_color="#A04000",
        )
        btn_find.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_apply_route = ctk.CTkButton(
            btn_frame, text="✔️ Apply Selected Path", state="disabled", command=self._apply_computed_route_to_mesh, fg_color="#27AE60", hover_color="#1E8449",
        )
        self.btn_apply_route.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        btn_reset_router = ctk.CTkButton(
            btn_frame, text="🔄 Reset Display", command=self._reset_router_display, fg_color="#7F8C8D", hover_color="#34495E",
        )
        btn_reset_router.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        res_card = ctk.CTkFrame(self.tab_router, corner_radius=8)
        res_card.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        lbl_res_head = ctk.CTkFrame(res_card, fg_color="transparent")
        lbl_res_head.pack(fill="x", padx=10, pady=(8, 2))
        
        ctk.CTkLabel(lbl_res_head, text="Synthesis Results & Path Trace:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.cmb_path_selector = ctk.CTkComboBox(lbl_res_head, width=150, values=["No Paths Found"], command=self._on_path_selection_change)
        self.cmb_path_selector.pack(side="right")

        self.txt_route_result = ctk.CTkTextbox(res_card, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_route_result.pack(fill="both", expand=True, padx=10, pady=8)

    def _reset_router_display(self):
        for line in self.active_route_lines + self.alt_route_lines:
            try:
                line.remove()
            except Exception:
                pass
        self.active_route_lines.clear()
        self.alt_route_lines.clear()
        self.canvas.draw_idle()
        
        self.last_computed_paths = []
        self.cmb_path_selector.configure(values=["No Paths Found"])
        self.cmb_path_selector.set("No Paths Found")
        self.txt_route_result.delete("1.0", tk.END)
        self.btn_apply_route.configure(state="disabled")

    def _set_picking_mode(self, mode):
        self.picking_target = mode
        
        # Reset all buttons to default state first
        if hasattr(self, 'btn_pick_src'): 
            self.btn_pick_src.configure(text="📌 Pick from Mesh Canvas", fg_color="#34495E")
        if hasattr(self, 'btn_pick_dst'): 
            self.btn_pick_dst.configure(text="📌 Pick from Mesh Canvas", fg_color="#34495E")
        if hasattr(self, 'btn_matrix_pick_src'): 
            self.btn_matrix_pick_src.configure(text="📌 Pick", fg_color="#34495E")
        if hasattr(self, 'btn_matrix_pick_dst'): 
            self.btn_matrix_pick_dst.configure(text="📌 Pick", fg_color="#34495E")

        # Set specific button to active state based on mode
        if mode == "SRC":
            if hasattr(self, 'btn_pick_src'): self.btn_pick_src.configure(text="👉 Click Port on Canvas...", fg_color="#00A896")
        elif mode == "DST":
            if hasattr(self, 'btn_pick_dst'): self.btn_pick_dst.configure(text="👉 Click Port on Canvas...", fg_color="#9B59B6")
        elif mode == "MATRIX_SRC":
            if hasattr(self, 'btn_matrix_pick_src'): self.btn_matrix_pick_src.configure(text="👉 Click Port...", fg_color="#00A896")
        elif mode == "MATRIX_DST":
            if hasattr(self, 'btn_matrix_pick_dst'): self.btn_matrix_pick_dst.configure(text="👉 Click Port...", fg_color="#9B59B6")

    def _on_src_combo_change(self, choice):
        self._update_router_port_marker("SRC", choice)

    def _on_dst_combo_change(self, choice):
        self._update_router_port_marker("DST", choice)

    def _compute_and_display_route(self):
        src = self.cmb_route_src.get()
        dst = self.cmb_route_dst.get()
        r_mode = self.router_mode_var.get()

        for line in self.active_route_lines + self.alt_route_lines + self.matrix_route_lines:
            try:
                line.remove()
            except Exception:
                pass
        self.active_route_lines.clear()
        self.alt_route_lines.clear()
        self.matrix_route_lines.clear()

        self._update_router_port_marker("SRC", src)
        self._update_router_port_marker("DST", dst)

        paths, msg = self.graph.find_multipaths(src, dst, constraint_mode=r_mode, max_paths=5)
        self.txt_route_result.delete("1.0", tk.END)

        if not paths:
            self.txt_route_result.insert(tk.END, f"❌ Routing Failed:\n{msg}\n")
            self.btn_apply_route.configure(state="disabled")
            self.last_computed_paths = []
            self.cmb_path_selector.configure(values=["No Paths Found"])
            self.cmb_path_selector.set("No Paths Found")
            self.canvas.draw_idle()
            return

        self.last_computed_paths = paths
        path_labels = [f"Alternative Path {i+1} ({len(p['path'])-1} Hops)" for i, p in enumerate(paths)]
        self.cmb_path_selector.configure(values=path_labels)
        
        self.btn_apply_route.configure(state="normal")
        
        # Display the first/shortest path by default
        self.cmb_path_selector.set(path_labels[0])
        self._on_path_selection_change(path_labels[0])

    def _on_path_selection_change(self, choice):
        if not self.last_computed_paths:
            return
            
        try:
            self.selected_path_idx = int(choice.split(" ")[2]) - 1
        except Exception:
            self.selected_path_idx = 0

        route_data = self.last_computed_paths[self.selected_path_idx]
        path = route_data["path"]
        states = route_data["states"]
        hops = len(path) - 1

        self.txt_route_result.delete("1.0", tk.END)
        summary = (
            f"✅ Route Successfully Synthesized (Loop-Free Progressive Route)!\n"
            f"--------------------------------------------------\n"
            f"Source Port:        {path[0]}\n"
            f"Destination Port:   {path[-1]}\n"
            f"Total Optical Hops: {hops}\n"
            f"MZIs Traversed:     {len(states)}\n"
            f"--------------------------------------------------\n"
            f"Required MZI State Configurations:\n"
        )
        for mzi_tag, req_st in states.items():
            summary += f"  • {mzi_tag:18s} ➔ Set to {req_st} ({'Bar' if req_st == 'BS' else 'Cross'})\n"

        summary += "\nSequential Optical Waveguide Path:\n"
        for i, p in enumerate(path):
            summary += f"  [{i:02d}] {p}\n"

        self.txt_route_result.insert(tk.END, summary)
        
        # Redraw lines
        for line in self.active_route_lines + self.alt_route_lines + self.matrix_route_lines:
            try:
                line.remove()
            except Exception:
                pass
        self.active_route_lines.clear()
        self.alt_route_lines.clear()
        self.matrix_route_lines.clear()

        # Draw alternative paths in faint dashed blue
        for alt_idx, alt_route in enumerate(self.last_computed_paths):
            if alt_idx == self.selected_path_idx:
                continue
            alt_p = alt_route["path"]
            for i in range(len(alt_p) - 1):
                p1, p2 = alt_p[i], alt_p[i + 1]
                if p1 in self.port_coords and p2 in self.port_coords:
                    x1, y1 = self.port_coords[p1]
                    x2, y2 = self.port_coords[p2]
                    line_artist, = self.ax.plot(
                        [x1, x2], [y1, y2], color="#3498DB", lw=1.5, zorder=7, linestyle="--", alpha=0.5
                    )
                    self.alt_route_lines.append(line_artist)

        # Draw selected primary route in solid thick orange
        for i in range(len(path) - 1):
            p1_name = path[i]
            p2_name = path[i + 1]
            if p1_name in self.port_coords and p2_name in self.port_coords:
                x1, y1 = self.port_coords[p1_name]
                x2, y2 = self.port_coords[p2_name]
                line_artist, = self.ax.plot(
                    [x1, x2], [y1, y2], color="#FF7700", lw=3.2, zorder=9, linestyle="-"
                )
                self.active_route_lines.append(line_artist)

        self.canvas.draw_idle()

    def _apply_computed_route_to_mesh(self):
        if not self.last_computed_paths:
            return

        states = self.last_computed_paths[self.selected_path_idx]["states"]
        for mzi_tag, new_state in states.items():
            if mzi_tag in self.mzi_data:
                cfg = STATE_CONFIGS[new_state]
                d = self.mzi_data[mzi_tag]
                d["state"] = new_state
                d["tpH_v"] = cfg["tpH_v"]
                d["tpH_p"] = cfg["tpH_p"]
                d["btH_v"] = cfg["btH_v"]
                d["btH_p"] = cfg["btH_p"]
                self.patches_dict[mzi_tag].set_facecolor(cfg["color"])
                for t in self.ax.texts:
                    if t.get_text() == mzi_tag:
                        t.set_color("white" if "DEF_" in new_state else "black")

        self.is_modified = True
        self._build_topology_connections()
        self._sync_tbu_tab()
        self._populate_port_table()
        self._update_home_metrics()
        self.canvas.draw_idle()

        messagebox.showinfo(
            "Routing Applied",
            f"Successfully applied states to {len(states)} MZI units along the chosen optical route."
        )

    # -------------------------------------------------------------
    # NEW TAB 7: PERMUTATION MATRIX COMPILER
    # -------------------------------------------------------------
    def _build_matrix_tab(self):
        lbl_head = ctk.CTkLabel(
            self.tab_matrix, text="Simultaneous Permutation Matrix Compiler", font=ctk.CTkFont(size=17, weight="bold")
        )
        lbl_head.pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(self.tab_matrix, text="Synthesize multiple non-conflicting optical channels simultaneously.", text_color="gray").pack(anchor="w", padx=10, pady=(0, 10))

        frame_sel = ctk.CTkFrame(self.tab_matrix, corner_radius=8)
        frame_sel.pack(fill="x", padx=10, pady=5)

        # Connection Pair Setup
        ctk.CTkLabel(frame_sel, text="Source Port:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="e")
        self.cmb_matrix_src = ctk.CTkComboBox(frame_sel, width=150, values=[], command=lambda choice: self._update_router_port_marker("SRC", choice))
        self.cmb_matrix_src.grid(row=0, column=1, padx=5, pady=(10, 5))
        
        self.btn_matrix_pick_src = ctk.CTkButton(
            frame_sel, text="📌 Pick", width=60, 
            command=lambda: self._set_picking_mode("MATRIX_SRC"),
            fg_color="#34495E", hover_color="#1A5276"
        )
        self.btn_matrix_pick_src.grid(row=0, column=2, padx=5, pady=(10, 5))

        ctk.CTkLabel(frame_sel, text="➔ Dest Port:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=(5, 10), sticky="e")
        self.cmb_matrix_dst = ctk.CTkComboBox(frame_sel, width=150, values=[], command=lambda choice: self._update_router_port_marker("DST", choice))
        self.cmb_matrix_dst.grid(row=1, column=1, padx=5, pady=(5, 10))

        self.btn_matrix_pick_dst = ctk.CTkButton(
            frame_sel, text="📌 Pick", width=60, 
            command=lambda: self._set_picking_mode("MATRIX_DST"),
            fg_color="#34495E", hover_color="#1A5276"
        )
        self.btn_matrix_pick_dst.grid(row=1, column=2, padx=5, pady=(5, 10))

        btn_add = ctk.CTkButton(frame_sel, text="➕ Add Link", width=100, command=self._add_matrix_connection)
        btn_add.grid(row=0, column=3, rowspan=2, padx=20, pady=10, sticky="ns")

        # List of Connections Treeview
        self.matrix_tree_frame = ctk.CTkFrame(self.tab_matrix)
        self.matrix_tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("id", "src", "dst")
        self.matrix_tree = ttk.Treeview(self.matrix_tree_frame, columns=columns, show="headings", height=8)
        self.matrix_tree.heading("id", text="Link #")
        self.matrix_tree.heading("src", text="Source Port (Tx)")
        self.matrix_tree.heading("dst", text="Destination Port (Rx)")

        self.matrix_tree.column("id", width=60, anchor="center")
        self.matrix_tree.column("src", width=180, anchor="center")
        self.matrix_tree.column("dst", width=180, anchor="center")
        self.matrix_tree.pack(side="left", fill="both", expand=True)

        btn_box = ctk.CTkFrame(self.matrix_tree_frame, fg_color="transparent")
        btn_box.pack(side="right", fill="y", padx=5)

        ctk.CTkButton(btn_box, text="❌ Remove Selected", width=120, fg_color="#C0392B", hover_color="#922B21", command=self._remove_matrix_connection).pack(pady=5)
        ctk.CTkButton(btn_box, text="🗑️ Clear All", width=120, fg_color="#7F8C8D", hover_color="#34495E", command=self._clear_matrix_connections).pack(pady=5)

        # Action Area
        action_top = ctk.CTkFrame(self.tab_matrix, fg_color="transparent")
        action_top.pack(fill="x", padx=10, pady=(5, 0))

        self.chk_wipe_mesh = ctk.CTkCheckBox(action_top, text="Wipe Mesh to 'AV' before compiling (Preserves Defects)")
        self.chk_wipe_mesh.select()
        self.chk_wipe_mesh.pack(side="left", padx=5, pady=5)
        
        self.chk_match_length = ctk.CTkCheckBox(action_top, text="Enforce Path-Length Matching (Coherent Computing)")
        self.chk_match_length.pack(side="left", padx=15, pady=5)

        action_bottom = ctk.CTkFrame(self.tab_matrix)
        action_bottom.pack(fill="x", padx=10, pady=5)

        btn_compile = ctk.CTkButton(action_bottom, text="🚀 Compute Preview", fg_color="#D35400", hover_color="#A04000", command=self._compile_matrix)
        btn_compile.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_apply_matrix = ctk.CTkButton(action_bottom, text="✔️ Apply Matrix", state="disabled", fg_color="#27AE60", hover_color="#1E8449", command=self._apply_matrix_route)
        self.btn_apply_matrix.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        btn_reset = ctk.CTkButton(action_bottom, text="🔄 Reset Display", fg_color="#7F8C8D", hover_color="#34495E", command=self._reset_matrix_display)
        btn_reset.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        action_bottom.grid_columnconfigure((0, 1, 2), weight=1)

        self.txt_matrix_result = ctk.CTkTextbox(self.tab_matrix, height=100, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_matrix_result.pack(fill="x", padx=10, pady=10)

    def _add_matrix_connection(self):
        src = self.cmb_matrix_src.get()
        dst = self.cmb_matrix_dst.get()

        if not src or not dst: return
        if src == dst:
            messagebox.showwarning("Invalid Link", "Source and Destination cannot be the same.")
            return

        for p in self.matrix_connections:
            if p[0] == src or p[1] == dst:
                messagebox.showwarning("Conflict", f"Port {p[0]} or {p[1]} is already used in the permutation matrix.")
                return

        self.matrix_connections.append((src, dst))
        self._refresh_matrix_tree()

    def _remove_matrix_connection(self):
        selected = self.matrix_tree.selection()
        if not selected: return
        idx = int(self.matrix_tree.item(selected[0], "values")[0]) - 1
        del self.matrix_connections[idx]
        self._refresh_matrix_tree()

    def _clear_matrix_connections(self):
        self.matrix_connections.clear()
        self._refresh_matrix_tree()

    def _refresh_matrix_tree(self):
        for row in self.matrix_tree.get_children():
            self.matrix_tree.delete(row)
        for i, (src, dst) in enumerate(self.matrix_connections):
            self.matrix_tree.insert("", "end", values=(i+1, src, dst))

    def _apply_states_silent(self, state_dict):
        """Applies states dynamically to the mesh data without triggering a GUI redraw."""
        for mzi_tag, new_state in state_dict.items():
            if mzi_tag in self.mzi_data:
                # Protect defects from being overwritten by NORMAL states
                if self.mzi_data[mzi_tag]["state"].startswith("DEF_") and not new_state.startswith("DEF_"):
                    continue
                    
                cfg = STATE_CONFIGS[new_state]
                d = self.mzi_data[mzi_tag]
                d["state"] = new_state
                d["tpH_v"] = cfg["tpH_v"]
                d["tpH_p"] = cfg["tpH_p"]
                d["btH_v"] = cfg["btH_v"]
                d["btH_p"] = cfg["btH_p"]
                self.patches_dict[mzi_tag].set_facecolor(cfg["color"])
                
                for t in self.ax.texts:
                    if t.get_text() == mzi_tag:
                        t.set_color("white" if "DEF_" in new_state else "black")
        
        self._build_topology_connections()

    def _compile_matrix(self):
        if not self.matrix_connections:
            messagebox.showinfo("Empty Matrix", "Please add source-destination links to compile.")
            return

        is_match_length = self.chk_match_length.get()

        self.txt_matrix_result.delete("1.0", tk.END)
        self.txt_matrix_result.insert(tk.END, "⚙️ Compiling Matrix Preview (with Rip-Up & Reroute)...\n")
        if is_match_length:
            self.txt_matrix_result.insert(tk.END, "⏳ Mode: Coherent Path-Length Matching Enabled\n")
        self.txt_matrix_result.update()

        # Backup original states
        backup_states = {tag: d["state"] for tag, d in self.mzi_data.items()}

        starting_states = dict(backup_states)
        if self.chk_wipe_mesh.get():
            # Wipe ONLY non-defective MZIs
            starting_states = {tag: d["state"] if d["state"].startswith("DEF_") else "AV" for tag, d in self.mzi_data.items()}
            
        self._apply_states_silent(starting_states)

        # Backtracking Router
        def backtrack_route(idx, current_mzi_states, target_len):
            if idx == len(self.matrix_connections):
                return True, [], current_mzi_states

            src, dst = self.matrix_connections[idx]
            self._apply_states_silent(current_mzi_states)
            
            # Request many alternative paths for a better chance of avoiding blocks
            paths, msg = self.graph.find_multipaths(
                src, dst, constraint_mode="SHARED", max_paths=30, 
                max_depth=target_len if target_len else 40,
                target_length=target_len
            )
            
            for p in paths:
                next_states = dict(current_mzi_states)
                next_states.update(p["states"])
                
                success, future_paths, final_states = backtrack_route(idx + 1, next_states, target_len)
                if success:
                    return True, [(src, dst, p)] + future_paths, final_states
            
            self._apply_states_silent(current_mzi_states)
            return False, [], None

        success = False
        compiled_paths = []
        final_preview_states = {}

        if is_match_length:
            self.txt_matrix_result.insert(tk.END, "  Calculating base minimum lengths...\n")
            self.txt_matrix_result.update()
            
            base_lengths = []
            for src, dst in self.matrix_connections:
                paths, _ = self.graph.find_multipaths(src, dst, constraint_mode="SHARED", max_paths=1)
                if not paths:
                    self.txt_matrix_result.insert(tk.END, f"❌ Impossible to route {src} ➔ {dst} individually.\n")
                    self._apply_states_silent(backup_states)
                    return
                base_lengths.append(len(paths[0]['path']) - 1)
            
            target_L = max(base_lengths)
            max_L = target_L + 6 # Allow up to +6 hops of detour for phase matching

            for tl in range(target_L, max_L + 1):
                self.txt_matrix_result.insert(tk.END, f"  Attempting simultaneous routing at Length = {tl} hops...\n")
                self.txt_matrix_result.update()
                
                success, compiled_paths, final_preview_states = backtrack_route(0, starting_states, tl)
                if success:
                    break
        else:
            success, compiled_paths, final_preview_states = backtrack_route(0, starting_states, None)

        if success:
            for i, (src, dst, best_path) in enumerate(compiled_paths):
                self.txt_matrix_result.insert(tk.END, f"  Channel {i+1} Routed: {src} ➔ {dst} ({len(best_path['path'])-1} Hops)\n")
            
            self.matrix_preview_states = final_preview_states
            self._apply_states_silent(backup_states)

            self.txt_matrix_result.insert(tk.END, "\n✅ Matrix Preview Computed Successfully!\nClick 'Apply Matrix' to commit.")
            
            self._draw_matrix_paths(compiled_paths)
            self.canvas.draw_idle()
            self.btn_apply_matrix.configure(state="normal")
        else:
            if is_match_length:
                self.txt_matrix_result.insert(tk.END, "\n❌ Matrix Compilation Failed!\nCould not find path-length matched routes within constraints.")
            else:
                self.txt_matrix_result.insert(tk.END, "\n❌ Matrix Compilation Failed!\nCould not resolve non-conflicting paths even with backtracking.")
            
            self._apply_states_silent(backup_states)
            
            for line in self.matrix_route_lines:
                try: line.remove()
                except Exception: pass
            self.matrix_route_lines.clear()
            self.canvas.draw_idle()
            
            if hasattr(self, 'btn_apply_matrix'):
                self.btn_apply_matrix.configure(state="disabled")
            self.matrix_preview_states = None

    def _apply_matrix_route(self):
        if not hasattr(self, "matrix_preview_states") or not self.matrix_preview_states:
            return
            
        self._apply_states_silent(self.matrix_preview_states)
        self.is_modified = True
        self._sync_tbu_tab()
        self._populate_port_table()
        self._update_home_metrics()
        self.canvas.draw_idle()
        
        self.txt_matrix_result.insert(tk.END, "\n\n✔️ Matrix Successfully Applied to Mesh!")
        self.btn_apply_matrix.configure(state="disabled")
        self.matrix_preview_states = None

    def _reset_matrix_display(self):
        # Clear canvas paths
        for line in self.matrix_route_lines:
            try: line.remove()
            except Exception: pass
        self.matrix_route_lines.clear()
        self.canvas.draw_idle()
        
        self.matrix_preview_states = None
        if hasattr(self, 'btn_apply_matrix'):
            self.btn_apply_matrix.configure(state="disabled")
        self.txt_matrix_result.delete("1.0", tk.END)

    def _draw_matrix_paths(self, compiled_data):
        # Clear existing paths across all tools
        for line in self.matrix_route_lines + self.active_route_lines + self.alt_route_lines:
            try: line.remove()
            except Exception: pass
        self.matrix_route_lines.clear()
        self.active_route_lines.clear()
        self.alt_route_lines.clear()

        # Draw each channel with a unique color
        for idx, (src, dst, path_data) in enumerate(compiled_data):
            color = self.channel_colors[idx % len(self.channel_colors)]
            path = path_data["path"]
            
            for i in range(len(path) - 1):
                p1_name = path[i]
                p2_name = path[i + 1]
                if p1_name in self.port_coords and p2_name in self.port_coords:
                    x1, y1 = self.port_coords[p1_name]
                    x2, y2 = self.port_coords[p2_name]
                    
                    # Offset the line slightly based on channel index to avoid identical overlaps visually masking each other
                    offset = (idx * 0.015) - 0.03 
                    
                    line_artist, = self.ax.plot(
                        [x1+offset, x2+offset], [y1+offset, y2+offset], 
                        color=color, lw=3.0, zorder=8, linestyle="-"
                    )
                    self.matrix_route_lines.append(line_artist)

    # -------------------------------------------------------------
    # Helper to refresh dropdowns globally
    # -------------------------------------------------------------
    def _refresh_router_port_dropdowns(self):
        all_ports = []
        for tag in self.mzi_data:
            for p in ["Opt1", "Opt2", "Opt3", "Opt4"]:
                all_ports.append(f"{tag}_{p}")

        all_ports.sort()
        if hasattr(self, "cmb_route_src"):
            self.cmb_route_src.configure(values=all_ports)
            self.cmb_route_dst.configure(values=all_ports)
            if all_ports:
                self.cmb_route_src.set(all_ports[0])
                self.cmb_route_dst.set(all_ports[-1])
                self._update_router_port_marker("SRC", all_ports[0])
                self._update_router_port_marker("DST", all_ports[-1])

        if hasattr(self, "cmb_matrix_src"):
            self.cmb_matrix_src.configure(values=all_ports)
            self.cmb_matrix_dst.configure(values=all_ports)
            if all_ports:
                self.cmb_matrix_src.set(all_ports[0])
                self.cmb_matrix_dst.set(all_ports[-1])


if __name__ == "__main__":
    app = PhotonicMeshStudio()
    try:
        app.mainloop()
    except (KeyboardInterrupt, tk.TclError):
        pass
    finally:
        plt.close("all")