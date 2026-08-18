<p align="center">
  <img src="assets\banner.png" alt="Photonic Hexagonal Mesh Studio Banner" width="700"/>
</p>

# ⬡ Photonic Hexagonal Mesh Studio (TBU Controller Suite)

> **A Comprehensive Digital Twin and Control Software Architecture for Programmable Photonic Integrated Circuits (PICs) and Field-Programmable Photonic Gate Arrays (FPPGAs)[cite: 5, 6].**

---

## 👨‍💻 Creator & Lead Architect
**Ayush Soni** *Proprietary & Confidential Toolkit — Patent Pending (2026)*

---

## 📑 Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [The Paradigm Shift: Analog Programmable Photonic Computation](#2-the-paradigm-shift)
3. [Core Hardware Abstraction: Tunable Basic Units (TBUs)](#3-core-hardware-abstraction)
4. [Topological Superiority: The Hexagonal (Honeycomb) Lattice](#4-topological-superiority)
5. [Mathematical Engine & Physical Solvers](#5-mathematical-engine)
6. [Software Suite Features & Capabilities](#6-software-suite-features)
7. [Industrial & Scientific Applications](#7-industrial--scientific-applications)
8. [Technology Stack & Requirements](#8-technology-stack)
9. [Installation & Execution](#9-installation--execution)
10. [Intellectual Property & Licensing](#10-intellectual-property)

---

## 🚀 1. Executive Summary <a name="1-executive-summary"></a>

**Photonic Hexagonal Mesh Studio** is an advanced, high-performance software suite meticulously engineered to bridge the critical gap between abstract mathematical topologies and physical photonic hardware[cite: 5, 7]. 

As the demands of artificial intelligence, high-frequency signal processing, and real-time physical simulations push the boundaries of traditional silicon electronics, this studio provides the foundational operating system for **Analog Programmable Photonic Computation (APC)**[cite: 7]. By orchestrating a vast network of phase-shifting nodes arranged in a honeycomb lattice, this tool enables engineers to compile complex differential equations, multi-channel optical routes, and unitary matrix transformations into electrical control signals that dictate the flow of light on a semiconductor chip[cite: 5, 7].

---

## ⚡ 2. The Paradigm Shift: Analog Programmable Photonic Computation <a name="2-the-paradigm-shift"></a>

* Traditional digital von-Neumann architectures suffer from inherent latency and power bottlenecks when performing the massive parallel matrix computations required for neural networks and continuous physical modeling[cite: 7].
* This software suite leverages APC, an architecture that performs calculations natively at the speed of light[cite: 7]. 
* Instead of shuffling bits between memory and a CPU, computations occur continuously as photons propagate through cascaded interferometers[cite: 7]. 
* The optical mesh essentially acts as a highly specialized, reprogrammable analog computer capable of executing continuous matrix-vector multiplications with near-zero latency and orders of magnitude lower power consumption[cite: 7].

---

## 🔲 3. Core Hardware Abstraction: Tunable Basic Units (TBUs) <a name="3-core-hardware-abstraction"></a>

At the heart of the simulator and the physical PIC is the **Tunable Basic Unit (TBU)**[cite: 6]. Physically, this is realized as a balanced Mach–Zehnder Interferometer (MZI) equipped with dual-drive thermo-optic or electro-optic phase modulators[cite: 5, 6].

The software maps high-level routing demands into specific physical states for each TBU across the mesh.

<p align="center">
  <img src="assets\img2.png" alt="TBU Settings and Hardware Control" width="800"/>
  <br>
  <em>Figure 1: TBU Settings interface showcasing granular control over state presets and phase shifter voltages.</em>
</p>

### Fundamental Operating States

| State | Optical Function | Transfer Characteristics | Application in Mesh |
| :--- | :--- | :--- | :--- |
| **Bar State (BS)** | Direct Throughput | Bar = 1.0, Cross = 0.0 | Bypassing nodes, straight-line routing[cite: 5, 6]. |
| **Cross State (CS)** | Complete Diagonal Crossover | Bar = 0.0, Cross = 1.0 | Switching tracks, intersection routing[cite: 5, 6]. |
| **Tunable Coupler (TC)** | Variable Power Splitting | 0.0 < Bar < 1.0 | SVD matrix weighting, signal broadcasting[cite: 5, 6]. |

### Interactive Defect Modeling
To design robust optical circuits, the software includes a physical fault-injection system[cite: 5]. Users can interactively trigger failure modes to test the resilience of their routing algorithms:
* **`DEF_BS` (Stuck Bar):** The phase shifter is permanently burned out in the straight-through state[cite: 5].
* **`DEF_CS` (Stuck Cross):** The phase shifter is locked in the crossover state[cite: 5].
* **`DEF_DEAD` (Opaque):** Catastrophic waveguide failure; no light passes through the node[cite: 5].

---

## ⬡ 4. Topological Superiority: The Hexagonal (Honeycomb) Lattice <a name="4-topological-superiority"></a>

While early programmable photonics relied on square (Manhattan) or triangular grids, this studio exclusively compiles for **Hexagonal Mesh Configurations**[cite: 5, 6].

**Why Honeycomb?**
* **Maximized Routing Flexibility:** Honeycomb lattices provide a higher degree of spatial freedom, allowing multi-path routing with significantly fewer crossing conflicts[cite: 6].
* **Reduced Phase Error Accumulation:** The topology inherently requires fewer TBUs per average path length compared to square grids, minimizing insertion loss and thermal crosstalk[cite: 6].
* **Superior Packing Density:** Hexagonal packing allows the maximum number of computational gates per square millimeter on the silicon-on-insulator (SOI) wafer[cite: 6].

---

## 📐 5. Mathematical Engine & Physical Solvers <a name="5-mathematical-engine"></a>

The studio is not just a routing tool; it is a mathematical compiler. It translates non-unitary continuous-time systems into passive, energy-conserving optical instructions[cite: 7].

### Differential Equation Solvers
The software is capable of modeling second-order linear differential equations natively in the optical domain[cite: 7]. For example, a Damped Harmonic Oscillator (DHM) system can be transformed into a state-space representation, allowing the physical dynamics to be computed directly by the optical mesh[cite: 7].

### Singular Value Decomposition (SVD) Optical Bridge
Because the physical optical mesh is unitary (energy-conserving), it cannot natively represent a non-unitary matrix (such as the state-space matrix of a system with friction or damping)[cite: 7]. The software bridges this hardware limitation via SVD factorization[cite: 7]:

* **Input Rotation:** The software compiles the orthogonal input matrix into the first layer of MZIs to perform a lossless rotation of the input optical vector[cite: 7].
* **Diagonal Attenuation:** The singular scaling values are normalized to a maximum of 1.0[cite: 7]. The software configures a middle layer of MZIs in Tunable Coupler (TC) mode to act as variable optical attenuators (VOAs), physically discarding excess energy to represent mathematical damping[cite: 7].
* **Output Rotation:** The final orthogonal transformation maps the scaled optical signals back to the target basis for accurate photodiode detection[cite: 7].

---

## ✨ 6. Software Suite Features & Capabilities <a name="6-software-suite-features"></a>

* **Interactive Digital Twin Dashboard:** Powered by `customtkinter` and embedded `matplotlib` canvases[cite: 5]. Features a high-performance dark-mode rendering of the hardware mesh, dynamic hover tooltips, and real-time visualization of TBU states[cite: 5].

<p align="center">
  <img src="assets\img3.png" alt="Multipath Optical Router Tracing" width="800"/>
  <br>
  <em>Figure 2: Multipath Optical Router interface actively synthesizing a loop-free progressive route across the hexagonal mesh.</em>
</p>

* **Multipath Soft-Routing Compiler:** An advanced graph-search engine utilizing queue-based algorithms adapted for optical constraints[cite: 5]. Supports strictly available nodes, shared non-conflicting paths, and priority-override capabilities[cite: 5].
* **Simultaneous Permutation Matrix Compiler:** Allows users to synthesize multiple non-conflicting optical channels simultaneously[cite: 5]. 

<p align="center">
  <img src="assets\img1.png" alt="Simultaneous Permutation Matrix Compiler" width="800"/>
  <br>
  <em>Figure 3: Matrix Compiler executing parallel multi-channel routing with path-length matching.</em>
</p>

* **Coherent Path-Length Matching:** In interferometric optical computing, phase coherence is critical. The routing engine ensures that parallel multi-channel routes maintain equivalent optical path lengths to prevent unintended destructive interference[cite: 5].
* **Backtracking Rip-Up and Reroute:** An EDA-style autoplacer that automatically dynamically rips up low-priority optical routes if a high-priority path is blocked by topological constraints or physical hardware defects[cite: 5].
* **Hardware Interface Export:** Seamlessly serializes the computed optical graph into JSON netlists, complete with adjacency lists, boundary I/O ports, and voltage lookup tables for external tools[cite: 5].

---

## 💡 7. Industrial & Scientific Applications <a name="7-industrial--scientific-applications"></a>

The **Photonic Hexagonal Mesh Studio** enables the rapid prototyping of optical circuits for next-generation applications[cite: 7]:

* **Real-Time Machine Vision (Edge AI):** Performing instantaneous spatial differentiation and image convolution natively in the analog optical domain[cite: 7]. This allows for edge detection and feature extraction at tens of gigahertz without the power penalty of ADCs/DACs[cite: 7].
* **Aerospace & Hypersonic Guidance:** Solving ordinary and partial differential equations on-the-fly for ultra-low latency trajectory corrections, missile guidance kinetics, and thermal shock modeling[cite: 7].
* **LiDAR & Autonomous Kinematics:** Instantaneous matrix-vector processing for dynamic point-cloud transformations, essential for autonomous vehicle collision avoidance systems[cite: 7].
* **Thermal Conduction & Heat Diffusion Modeling:** Simulating spatial-temporal PDEs to model real-time thermal dissipation across high-power microelectronics and EV batteries[cite: 7].

---

## 🛠️ 8. Technology Stack & Requirements <a name="8-technology-stack"></a>

* **Core Logic Engine:** Python 3[cite: 5]
* **GUI Framework:** `customtkinter`, `tkinter`[cite: 5]
* **Numerical Computation:** `numpy`[cite: 5]
* **Visualization Renderer:** `matplotlib` (Embedded FigureCanvasTkAgg, NavigationToolbar2Tk)[cite: 5]
* **Data Structures:** Highly optimized custom routing graphs built using `collections.deque`[cite: 5]

---

## 📦 9. Installation & Execution <a name="9-installation--execution"></a>

To deploy the studio on your local workstation, follow these steps:

```bash
# 1. Clone the proprietary repository
git clone [https://github.com/AyushSoni/photonic-hexagonal-mesh-studio.git](https://github.com/AyushSoni/photonic-hexagonal-mesh-studio.git)

# 2. Navigate to the working directory
cd photonic-hexagonal-mesh-studio

# 3. Create a virtual environment (Recommended)
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# 4. Install dependencies
pip install customtkinter matplotlib numpy

# 5. Launch the primary interface
python test7_3.py
