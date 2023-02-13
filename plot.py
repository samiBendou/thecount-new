
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.figure as fig
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from core import *


def make_linear_trend(dates, data):
    x = mdates.date2num(dates)
    z = np.polyfit(x, data, 1)
    p = np.poly1d(z)
    xx = np.linspace(x.min(), x.max(), len(dates))
    return dates, p(xx)


def render_fig(fig: fig.Figure, title=None, date: datetime.date = None, pdf=None):
    plt.gcf().set_size_inches(8.3, 11.7)
    dated_title = None

    if title is not None:
        dated_title = title + \
            "" if date is None else date.strftime(
                "%A %d, %B %Y") + " ~ " + title
        fig.suptitle(dated_title, fontweight="bold")

    dated_file_title = title + \
        "" if date is None else date.strftime("%Y-%m-%d") + " " + title
    filename = "untitled" if title is None else dated_file_title.replace(
        " ", "_").lower()

    if pdf is not None:
        pdf.savefig(fig)
    else:
        fig.savefig(filename + ".pdf", format="pdf")
    fig.clf()


def render_ax(ax: plt.Axes, xl=None, yl=None, title=""):

    ax.grid(True)

    if xl is not None:
        ax.set_xlabel(xl)

    if yl is not None:
        ax.set_ylabel(yl)

    for tick in ax.get_xticklabels():
        tick.set_rotation(30)

    ax.set_title(title)


def plot_cash_flow(ax_flow: plt.Axes, ax_cumulative: plt.Axes, account: Account, dates, period: int = 1):
    balance = sample(dates, account.balance())
    gain = aggregate(dates, account.gain())
    loss = aggregate(dates, account.loss())

    rng_min = round(period/2)
    rng_max = len(dates) - rng_min
    smoothed_balance = smooth(period, balance)[rng_min:rng_max]
    smoothed_gain = smooth(period, gain)[rng_min:rng_max]
    smoothed_loss = smooth(period, loss)[rng_min:rng_max]
    smoothed_dates = dates[rng_min:rng_max]
    _, linear_balance = make_linear_trend(smoothed_dates, smoothed_balance)

    ax_flow.yaxis.set_major_formatter("{x} €")
    ax_cumulative.yaxis.set_major_formatter("{x} €")

    ax_flow.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_cumulative.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    ax_flow.text(smoothed_dates[-1], smoothed_balance[-1],
                 f"{round(smoothed_balance[-1])} €",  fontweight="bold")

    ax_flow.plot(smoothed_dates, smoothed_balance,
                 color="black", label="Balance")
    ax_flow.plot(smoothed_dates, linear_balance, "--", color="black")
    ax_flow.plot(smoothed_dates, smoothed_gain, color="green", label="Profit")
    ax_flow.plot(smoothed_dates, smoothed_loss, color="red", label="Loss")

    cumulated_gain = cumulate(gain)
    cumulated_loss = cumulate(loss)
    cumulated_pnl = [x - y for x, y in zip(cumulated_gain, cumulated_loss)]

    smoothed_cumulated_gain = smooth(period, cumulated_gain)[rng_min:rng_max]
    smoothed_cumulated_loss = smooth(period, cumulated_loss)[rng_min:rng_max]
    smoothed_cumulated_pnl = smooth(period, cumulated_pnl)[rng_min:rng_max]

    ax_cumulative.text(smoothed_dates[-1], smoothed_cumulated_gain[-1],
                       f"{round(smoothed_cumulated_gain[-1])} €", color="green",  fontweight="bold")
    ax_cumulative.text(smoothed_dates[-1], smoothed_cumulated_loss[-1],
                       f"{round(smoothed_cumulated_loss[-1])} €", color="red",  fontweight="bold")
    ax_cumulative.text(smoothed_dates[-1], smoothed_cumulated_pnl[-1],
                       f"{round(smoothed_cumulated_pnl[-1])} €", fontweight="bold")

    ax_cumulative.plot(smoothed_dates, smoothed_cumulated_pnl,
                       color="black", label="P&L")
    ax_cumulative.plot(smoothed_dates, smoothed_cumulated_gain,
                       color="green", label="Profit")
    ax_cumulative.plot(smoothed_dates, smoothed_cumulated_loss,
                       color="red", label="Loss")

    render_ax(ax_flow, title="Cash flow")
    render_ax(ax_cumulative, title="Profit & Loss")


def plot_repartition(ax_pos: plt.Axes, ax_neg: plt.Axes, amount_by_category, dates, title="Repartition", period=1):
    cumulated = list(map(lambda v: (v[0], cumulate(
        aggregate(dates, v[1]))), amount_by_category.items()))
    positive = list(filter(lambda y: max(y[1]) > 0, cumulated))
    negative = list(filter(lambda y: max(y[1]) <= 0, cumulated))

    ax_pos.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_neg.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    if (len(positive) > 0 and len(negative) > 0):
        ax_pos.yaxis.set_major_formatter('{x} €')
        ax_neg.yaxis.set_major_formatter('{x} €')
        ax_pos.stackplot(dates, list(map(lambda y: smooth(period, y[1]), positive)),
                         labels=list(map(lambda y: y[0], positive)))
        ax_neg.stackplot(dates, list(map(lambda y: smooth(period, invert(y[1])), negative)),
                         labels=list(map(lambda y: y[0], negative)))
        render_ax(ax_pos, title="Profit ~ " + title)
        render_ax(ax_neg, title="Loss ~ " + title)

    elif (len(negative) > 0):
        ax_neg.yaxis.set_major_formatter('{x} €')
        ax_neg.stackplot(dates, list(map(lambda y: smooth(period, invert(y[1])), negative)),
                         labels=list(map(lambda y: y[0], negative)))
        render_ax(ax_neg)

    elif (len(positive) > 0):
        ax_pos.yaxis.set_major_formatter('{x} €')
        ax_pos.stackplot(dates, list(map(lambda y: smooth(period, y[1]), positive)),
                         labels=list(map(lambda y: y[0], positive)))
        render_ax(ax_pos)


def plot_pie_repartition(ax: plt.Axes, amount_by_category, dates):
    cumulated = list(map(lambda v: (v[0], cumulate(
        aggregate(dates, v[1]))), amount_by_category.items()))

    positive = list(filter(lambda y: max(y[1]) > 0, cumulated))
    positive_labels = list(map(lambda y: y[0], positive))
    positive_values = list(map(lambda y: y[1][-1], positive))

    negative = list(filter(lambda y: max(y[1]) <= 0, cumulated))
    negative_labels = list(map(lambda y: y[0], negative))
    negative_values = list(map(lambda y: -y[1][-1], negative))

    if (len(negative) > 0 and sum(negative_values) > 0):
        ax.pie(negative_values, labels=negative_labels,
               radius=1,
               wedgeprops=dict(width=0.5, edgecolor="w"),
               autopct="%1.1f%%"
               )

        render_ax(ax)

    elif (len(positive) > 0 and sum(positive_values) > 0):
        ax.pie(positive_values, labels=positive_labels,
               radius=1,
               wedgeprops=dict(width=0.5, edgecolor="w"),
               autopct="%1.1f%%"
               )
        render_ax(ax)


def plot_bar_repartition(ax: plt.Axes, amount_by_category, dates):
    cumulated = list(map(lambda v: (v[0], cumulate(
        aggregate(dates, v[1]))), amount_by_category.items()))

    positive = list(filter(lambda y: max(y[1]) > 0, cumulated))
    positive_labels = list(map(lambda y: y[0], positive))
    positive_values = list(map(lambda y: y[1][-1], positive))

    negative = list(filter(lambda y: max(y[1]) <= 0, cumulated))
    negative_labels = list(map(lambda y: y[0], negative))
    negative_values = list(map(lambda y: -y[1][-1], negative))

    ax.yaxis.set_major_formatter('{x} €')

    if (len(negative) > 0):
        x = range(len(negative_labels))
        ax.bar(x, height=negative_values, tick_label=negative_labels,
               color=mcolors.TABLEAU_COLORS)

    elif (len(positive) > 0):
        x = range(len(positive_labels))
        ax.bar(x, height=positive_values, tick_label=positive_labels,
               color=mcolors.TABLEAU_COLORS)

    render_ax(ax)
    ax.set_xticks([])


def render_synthesis(export_account, dates, period=1):
    start = dates[0]
    end = dates[-1]

    with PdfPages(f"{start.isoformat()}_{end.isoformat()}_{1}_days_account_synthesis.pdf") as pdf:
        fig, ax = plt.subplots(4, 1, sharex=True)

        plot_cash_flow(ax[0], ax[1], export_account, dates, period=period)

        amount_by_category = export_account.by_category()
        amount_by_sub_category = export_account.by_sub_category()
        plot_repartition(ax[2], ax[3], amount_by_category,
                         dates, period=period)

        render_fig(fig, title="Account synthesis", date=end, pdf=pdf)
        plt.close(fig)

        fig, ax = plt.subplots(2, 1)
        plot_pie_repartition(ax[0], amount_by_category, dates)
        plot_bar_repartition(ax[1], amount_by_category, dates)

        render_fig(fig, title="Overall repartition", pdf=pdf)

        plt.close(fig)

        for category, amounts in amount_by_sub_category.items():
            fig, ax = plt.subplots(3, 1)
            plot_pie_repartition(ax[0], amounts, dates)
            plot_bar_repartition(ax[1], amounts, dates)
            plot_repartition(ax[2], ax[2], amounts, dates, period=period)

            render_fig(
                fig, title=f"Detailed Repartition ~ {category}", pdf=pdf)

            plt.close(fig)
