
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import imageio.v2 as imageio
import io

from simulation.phase_space import PhaseSpace, SymbolicState
from simulation.constraint import KarmicConstraintField
from simulation.attractor import Attractor
from simulation.observer import Observer
from simulation.visualizer import SymbolicVisualizer
from animator import SymbolicAnimator

st.title("Phase Drift Explorer")

# Sidebar Controls
theta = st.sidebar.slider("Collapse Threshold (θ)", 0.1, 2.0, 0.75, 0.05)
timesteps = st.sidebar.slider("Timesteps", 10, 100, 30, 1)
attractor_center = st.sidebar.slider("Attractor x Center", -2.0, 2.0, 0.0, 0.1)
observer_strength = st.sidebar.slider("Observer Influence", 0.0, 1.0, 0.1, 0.05)

# Button to run the sim
if st.button("Run Simulation"):
    st.write("✅ Simulation started...")

    ps = PhaseSpace(theta=theta)
    kce = KarmicConstraintField()
    viz = SymbolicVisualizer()

    def R(t): return np.sin(t)

    initial_state = SymbolicState(
        x=1.0,
        m=np.array([0.5, -0.5]),
        r=R
    )
    ps.add_state(initial_state)

    attractor = Attractor(center_x=attractor_center,
                          memory_pattern=np.array([0.0, 0.0]),
                          identity_function=lambda t: 0)

    observer = Observer(identity_function=lambda t: np.cos(t),
                        memory_vector=np.array([observer_strength, observer_strength]))

    collapse_flags = []

    for t in range(timesteps):
        current_states = ps.states

        def gradient_func(state):
            delta_k = observer.boundary_deformation(state, t)
            grad = kce.gradient(state, t, neighbor_states=current_states)
            grad[0] += delta_k
            return grad

        stabilized_states = []
        for state in current_states:
            new_x, new_m, new_r = attractor.stabilize(state, t)
            stabilized_states.append(SymbolicState(new_x, new_m, new_r))
        ps.states = stabilized_states

        grads = [gradient_func(state)[:2] for state in ps.states]
        collapsed_flags = [
            np.linalg.norm(np.concatenate([np.atleast_1d(g[0]), g[1]])) > ps.theta
            for g in grads
        ]
        collapse_flags.append(any(collapsed_flags))

        ps.step(gradient_func)
        viz.record(ps.states)

        st.text(f"Timestep {t+1} completed")

    st.session_state["viz_history"] = viz.history
    st.session_state["collapse_flags"] = collapse_flags

    anim = SymbolicAnimator(history=viz.history)

    # Final plot
    st.subheader("Symbolic Identity Dynamics")
    fig, ax = plt.subplots(figsize=(8, 6))
    for t_h, snapshot in enumerate(viz.history[:-1]):
        xs, ms = zip(*snapshot)
        ax.scatter(xs, ms, color='lightgray', alpha=0.3, s=20)

    if viz.history:
        xs, ms = zip(*viz.history[-1])
        color = 'red' if collapse_flags[-1] else 'blue'
        ax.scatter(xs, ms, c=color, s=60, edgecolor='black', linewidths=0.5)


    ax.set_xlabel('Symbolic Identity (x)')
    ax.set_ylabel('Memory Magnitude (||m||)')
    ax.set_title('Symbolic State at Final Timestep')
    ax.grid(True)
    st.pyplot(fig)

    # Midpoint
    st.subheader("Symbolic State at Midpoint")
    mid = len(viz.history) // 2
    fig_mid = anim.frame(mid, show=False)
    st.pyplot(fig_mid)

    # Collapse Timeline
    st.subheader("Collapse Timeline")
    fig2, ax2 = plt.subplots(figsize=(8, 3))
    ax2.plot(collapse_flags, label='Collapse Detected')
    ax2.set_xlabel('Timestep')
    ax2.set_ylabel('Collapse')
    ax2.set_title('Collapse Over Time')
    ax2.grid(True)
    ax2.legend()
    st.pyplot(fig2)

# Export GIF using persistent state
if "viz_history" in st.session_state:
    anim = SymbolicAnimator(history=st.session_state["viz_history"])

    if st.button("Export Animation as GIF"):
        tmp_gif = "symbolic_evolution.gif"
        anim.save_gif(tmp_gif)

        with open(tmp_gif, "rb") as f:
            st.download_button(
                label="Download GIF",
                data=f,
                file_name="symbolic_evolution.gif",
                mime="image/gif"
            )
else:
    st.warning("Run the simulation first before exporting animation.")
