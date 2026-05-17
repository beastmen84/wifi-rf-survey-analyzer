"""Helpers for applying user-drawn boundary masks to rendered map grids."""

import numpy as np


def get_boundary_mask_alpha(mask_image, grid_x, grid_y):
    if mask_image is None:
        return None

    width = grid_x.shape[0]
    height = grid_x.shape[1]
    alpha_image = mask_image.convert("RGBA").getchannel("A")
    alpha_image = alpha_image.resize((width, height))
    alpha = np.asarray(alpha_image, dtype=float).T / 255.0
    return np.clip(alpha, 0.0, 1.0)


def boundary_mask_fingerprint(mask_image):
    if mask_image is None:
        return None

    thumbnail = mask_image.convert("RGBA").resize((16, 16))
    return hash(thumbnail.tobytes())
