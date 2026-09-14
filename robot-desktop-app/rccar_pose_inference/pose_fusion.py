"""Confidence-weighted (inverse-variance) fusion of two distance estimates.

Used to combine the floor-plane (Ground) distance estimate with the ArUco
marker distance estimate (when a marker is visible), instead of one simply
overriding the other on any single noisy frame.
"""
from __future__ import annotations


def fuse_distance(dist_ground: float | None, dist_aruco: float | None,
                   sigma_ground: float, sigma_aruco: float) -> float | None:
    if dist_ground is None:
        return dist_aruco
    if dist_aruco is None:
        return dist_ground
    w_ground = 1.0 / (sigma_ground ** 2)
    w_aruco = 1.0 / (sigma_aruco ** 2)
    return (w_ground * dist_ground + w_aruco * dist_aruco) / (w_ground + w_aruco)
