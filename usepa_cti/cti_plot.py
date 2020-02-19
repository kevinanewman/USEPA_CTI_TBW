# -*- coding: utf-8 -*-
"""

cti_plot.py
==============

Plotting functions based on matplotlib pyplot

.. note::

    This is development code written by EPA staff and
    is intended only for evaluation purposes—it does not
    represent how we may or may not use the resulting
    output in the development or promulgation of future rules

@author: US EPA

"""

from __init__ import *

if cti_verbose:
    print('Loading %s...' % __name__)

import matplotlib.pyplot as plt



def label_xy(ax, x_label_str, y_label_str):
    """
    Label x-axis, y-axis and set axis title

    :param ax: plot (axis) to label
    :param x_label_str: x axis label
    :param y_label_str: y axis label
    """
    ax.set_xlabel(x_label_str, fontsize=9)
    ax.set_ylabel(y_label_str, fontsize=9)


def label_xyt(ax, x_label_str, y_label_str, title_str):
    """
    Label x-axis, y-axis and set axis title

    :param ax: plot (axis) to label
    :param x_label_str: x axis label
    :param y_label_str: y axis label
    :param title_str: axis title
    """
    ax.set_xlabel(x_label_str, fontsize=9)
    ax.set_ylabel(y_label_str, fontsize=9)
    ax.set_title(title_str, fontsize=9)


def lineat(ax, y, *args, **kwargs):
    """
    Plot a horizontal line

    :param ax: plot (axis) to draw on
    :param y: y value of line
    :param args: matplotlib pyplot arguments
    :param kwargs: matplotlib pyplot keyword arguments
    """
    xlim = ax.get_xlim()
    ax.plot(xlim, [y, y], *args, **kwargs)
    ax.set_xlim(xlim)


def vlineat(ax, x, *args, **kwargs):
    """

    Draw a vertical line at:

    :param ax: plot (axis) to draw on
    :param x: x value of line
    :param args: matplotlib pyplot arguments
    :param kwargs: matplotlib pyplot keyword arguments
    """
    ylim = ax.get_ylim()
    ax.plot([x, x], ylim, *args, **kwargs)
    ax.set_ylim(ylim)


def fplothg(x, y, *args, **kwargs):
    """
    Create a new figure window and plot Y v. X, activate plot grid

    :param x: x data points
    :param y: y data points
    :param args: matplotlib pyplot arguments
    :param kwargs: matplotlib pyplot keyword arguments
    :return: (figure, axis) tuple
    """
    fig, ax1 = plt.subplots()
    ax1.plot(x, y, *args, **kwargs)
    ax1.grid(True, which='both')
    return fig, ax1


def fplotyyhg(x, y, ylinespec, y2, y2linespec):
    """
    Create a new figure window and plot Y v. X and Y2 v. X, with independent vertical axes, activate plot grid

    :param x: x data points
    :param y: first set of y data points
    :param ylinespec: matplotlib line spec for first set of y data
    :param y2: second set of y data points
    :param y2linespec: matplotlib line spec for second set of y data
    :return: (figure, axis1, axis2) tuple
    """
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    ax1.plot(x, y, ylinespec)
    ax2.plot(x, y2, y2linespec)
    ax1.grid(True)
    # ax2.grid(True)
    return fig, ax1, ax2


if __name__ == '__main__':
    fig, ax = fplothg([1, 2, 3], [4, 5, 6], 'r-')
