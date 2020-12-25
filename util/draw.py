"""
By Jaerong
Helper functions for drawing a save_fig
"""

import matplotlib.pyplot as plt


def set_fig_size(w, h, ax=None):
    """ w, h: width, height in inches """
    if not ax: ax = plt.gca()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom
    figw = float(w) / (r - l)
    figh = float(h) / (t - b)
    ax.figure.set_size_inches(figw, figh)


def remove_right_top(ax):
    ax.spines['right'].set_visible(False), ax.spines['top'].set_visible(False)
