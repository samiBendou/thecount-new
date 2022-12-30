import csv
import datetime
import math

import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.figure as fig
import matplotlib.pyplot as plt
import numpy as np
import xlrd
from matplotlib.backends.backend_pdf import PdfPages

CURRENT_DATA = "current-data.csv"
EXPORT_FILE = "merge-export.csv"
IMPORT_FILE = "export_30_12_2022_18_01_14.xls"


def read_xls_file(filepath):
    book = xlrd.open_workbook(filepath, encoding_override="cp1252")
    sheet = book.sheet_by_index(0)
    return list(map(lambda i: sheet.row_values(i), range(0, sheet.nrows)))


def read_csv_file(filepath):
    with open(filepath, newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=";")
        data = list(map(lambda row: row, reader))
    return data


def write_csv_file(filepath, rows):
    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerows(rows)


def parse_french_date(date, delimiter="-"):
    values = list(map(int, date.split(delimiter)))
    return datetime.date(values[2], values[1], values[0])


def make_french_date(date, delimiter="-"):
    return date.strftime(f"%d{delimiter}%m{delimiter}%Y")


def some(array, predicate):
    return len(list(filter(predicate, array))) > 0


def unzip(zipped):
    return (list(map(lambda z: z[0], zipped)), list(map(lambda z: z[1], zipped)))


def make_linear_date(start, end, days=1):
    total_duration = end - start
    delta = datetime.timedelta(days=days)
    return list(map(lambda i: start + i * delta, range(math.ceil(total_duration.days / days))))


def group_by(keys, values):
    grouped = {}
    for key, value in zip(keys, values):
        try:
            grouped[key] += [value]
        except KeyError:
            grouped[key] = [value]

    return grouped


def sample(dates, data):
    new_data = {}
    for d in dates:
        try:
            new_data[d] = data[d][-1]
            last_known = new_data[d]
        except KeyError:
            try:
                new_data[d] = last_known
            except UnboundLocalError:
                new_data[d] = 0.0
                last_known = 0.0

    return unzip(sorted(new_data.items(), key=lambda i: i[0]))[1]


def aggregate(dates, data):
    try:
        new_data = {dates[0]: sum(data[dates[0]])}
    except KeyError:
        new_data = {dates[0]: 0.0}
    for current_date, next_date in zip(dates[:-1], dates[1:]):
        date_range = make_linear_date(current_date, next_date)

        try:
            new_data[next_date] = sum(data[next_date])
        except KeyError:
            new_data[next_date] = 0.0

        for d in date_range[1:]:
            try:
                new_data[next_date] += sum(data[d])
            except KeyError:
                new_data[next_date] += 0.0

    return unzip(sorted(new_data.items(), key=lambda i: i[0]))[1]


def cumulate(data):
    cumulated = [data[0]] + [0] * (len(data) - 1)
    for idx, x in enumerate(data[1:]):
        cumulated[idx + 1] = x + cumulated[idx]

    return cumulated


def invert(data):
    return list(map(lambda x: -x, data))


def make_linear_trend(dates, data):
    x = mdates.date2num(dates)
    z = np.polyfit(x, data, 1)
    p = np.poly1d(z)
    xx = np.linspace(x.min(), x.max(), len(dates))
    return dates, p(xx)


class Transaction:
    occured_at: datetime.date
    category: str
    sub_category: str
    label: str
    amount: float

    def __init__(self, occured_at, category, sub_category, label, amount):
        self.occured_at = occured_at
        self.category = category
        self.sub_category = sub_category
        self.label = label
        self.amount = amount

    def is_initial(self):
        return self.label == "initial"

    def to_export(self):
        return [
            make_french_date(self.occured_at),
            self.category,
            self.sub_category,
            self.label,
            str(self.amount).replace(".", ","),
        ]

    def is_same(self, other):
        is_same_date = self.occured_at == other.occured_at
        is_same_label = self.label == other.label
        is_same_amount = self.amount == other.amount
        return is_same_date and is_same_label and is_same_amount

    @ staticmethod
    def parse_import(row):
        occured_at = parse_french_date(row[0])
        category = row[1]
        sub_category = row[2]
        label = row[3]
        amount = float(row[4])
        return Transaction(occured_at, category, sub_category, label, amount)

    @ staticmethod
    def parse_current(row):
        occured_at = parse_french_date(row[1])
        category = row[2]
        sub_category = row[3]
        label = row[4]
        amount = float(row[5].replace(",", "."))
        return Transaction(occured_at, category, sub_category, label, amount)

    @ staticmethod
    def make_initial(occured_at, amount):
        return Transaction(occured_at=occured_at,
                           category="",
                           sub_category="",
                           label="initial",
                           amount=amount)


class Account:
    initial_balance: float
    transactions: list[Transaction]
    imported_at: datetime.date

    def __init__(self, initial_balance, imported_at, transactions):
        self.initial_balance = initial_balance
        self.imported_at = imported_at
        self.transactions = transactions

    @ staticmethod
    def parse_import(rows):
        final_balance = float(rows[0][2])
        imported_at = parse_french_date(
            rows[0][1].replace("Solde au ", ""), "/")
        transactions = list(map(Transaction.parse_import, rows[3:]))
        transactions.reverse()
        total_amount = sum(map(lambda t: t.amount, transactions))
        initial_balance = final_balance - total_amount
        return Account(initial_balance, imported_at, transactions)

    @ staticmethod
    def parse_current(rows):
        imported_at = parse_french_date(rows[0][7], "/")
        all_transactions = list(map(Transaction.parse_current, rows[1:]))
        initial_balance = float(list(
            filter(Transaction.is_initial, all_transactions))[0].amount)
        transactions = list(
            filter(lambda t: not Transaction.is_initial(t), all_transactions))
        return Account(initial_balance, imported_at, transactions)

    def to_export(self):
        header = ["Ordre",
                  "Date",
                  "Categorie",
                  "Sous Categorie",
                  "Libelle",
                  "Montant",
                  "",
                  make_french_date(self.imported_at, "/")]

        initial_date = self.transactions[0].occured_at - \
            datetime.timedelta(days=1)
        initial = Transaction.make_initial(initial_date, self.initial_balance)
        initial_row = [0, *initial.to_export()]

        rows = list(
            map(lambda t: [t[0] + 1, *t[1].to_export()], enumerate(self.transactions)))
        return [header, initial_row, *rows]

    def merge(self, other):
        if self.imported_at > other.imported_at:
            raise NotImplementedError

        initial_balance = self.initial_balance
        imported_at = other.imported_at
        last_occured_at = self.ended_at()

        old_transactions = list(filter(lambda t_self: not some(
            other.transactions, lambda t_other: t_other.is_same(t_self)), self.transactions))

        updated_transactions = list(filter(lambda t_other: some(
            self.transactions, lambda t_self: t_self.is_same(t_other)), other.transactions))

        new_transactions = list(filter(lambda t_other: t_other.occured_at > last_occured_at and not some(
            self.transactions, lambda t_self: t_self.is_same(t_other)), other.transactions))

        transactions = old_transactions + updated_transactions + new_transactions

        return Account(initial_balance, imported_at, transactions)

    def occured_at(self):
        return list(map(lambda t: t.occured_at, self.transactions))

    def balance(self):
        balance = [0] * (len(self.transactions) + 1)
        balance[0] = self.initial_balance
        for idx, transaction in enumerate(self.transactions):
            balance[idx + 1] = balance[idx] + transaction.amount

        return group_by(self.occured_at(), balance[1:])

    def gain(self):
        return group_by(self.occured_at(), list(map(lambda t: max(t.amount, 0), self.transactions)))

    def loss(self):
        return group_by(self.occured_at(), list(map(lambda t: max(-t.amount, 0), self.transactions)))

    def started_at(self):
        return self.transactions[0].occured_at

    def ended_at(self):
        return self.transactions[-1].occured_at

    def by_category(self):
        transactions = {}
        for t in self.transactions:
            try:
                transactions[t.category][t.occured_at] += [t.amount]
            except KeyError:
                try:
                    transactions[t.category][t.occured_at] = [t.amount]
                except KeyError:
                    transactions[t.category] = {t.occured_at: [t.amount]}

        return transactions

    def by_sub_category(self):
        transactions = {}
        for t in self.transactions:
            try:
                transactions[t.category][t.sub_category][t.occured_at] += [t.amount]
            except KeyError:
                try:
                    transactions[t.category][t.sub_category][t.occured_at] = [
                        t.amount]
                except KeyError:
                    try:
                        transactions[t.category][t.sub_category] = {
                            t.occured_at: [t.amount]}
                    except KeyError:
                        transactions[t.category] = {
                            t.sub_category: {t.occured_at: [t.amount]}}

        return transactions


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


def render_ax(ax: plt.Axes, xl=None, yl=None, legend=True, title=""):

    ax.grid(True)

    if legend is True:
        ax.legend(loc="upper left")

    if xl is not None:
        ax.set_xlabel(xl)

    if yl is not None:
        ax.set_ylabel(yl)

    for tick in ax.get_xticklabels():
        tick.set_rotation(30)

    ax.set_title(title)


def plot_cash_flow(ax_flow: plt.Axes, ax_cumulative: plt.Axes, account: Account, dates):
    balance = sample(dates, account.balance())
    gain = aggregate(dates, account.gain())
    loss = aggregate(dates, account.loss())
    _, linear_balance = make_linear_trend(dates, balance)

    ax_flow.yaxis.set_major_formatter("{x} €")
    ax_cumulative.yaxis.set_major_formatter("{x} €")

    ax_flow.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_cumulative.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    ax_flow.text(dates[-1], balance[-1],
                 f"{round(balance[-1])} €",  fontweight="bold")
    ax_flow.plot(dates, balance, color="black", label="Balance")
    ax_flow.plot(dates, linear_balance, "--", color="black")
    ax_flow.plot(dates, gain, color="green", label="Profit")
    ax_flow.plot(dates, loss, color="red", label="Loss")

    cumulated_gain = cumulate(gain)
    cumulated_loss = cumulate(loss)
    cumulated_pnl = [x - y for x, y in zip(cumulated_gain, cumulated_loss)]
    ax_cumulative.text(dates[-1], cumulated_gain[-1],
                       f"{round(cumulated_gain[-1])} €", color="green",  fontweight="bold")
    ax_cumulative.text(dates[-1], cumulated_loss[-1],
                       f"{round(cumulated_loss[-1])} €", color="red",  fontweight="bold")
    ax_cumulative.text(dates[-1], cumulated_pnl[-1],
                       f"{round(cumulated_pnl[-1])} €", fontweight="bold")
    ax_cumulative.plot(dates, cumulated_pnl, color="black", label="P&L")
    ax_cumulative.plot(dates, cumulated_gain, color="green", label="Profit")
    ax_cumulative.plot(dates, cumulated_loss, color="red", label="Loss")
    render_ax(ax_flow, title="Cash flow")
    render_ax(ax_cumulative, title="Profit & Loss")


def plot_repartition(ax_pos: plt.Axes, ax_neg: plt.Axes, amount_by_category, dates, title="Repartition"):
    cumulated = list(map(lambda v: (v[0], cumulate(
        aggregate(dates, v[1]))), amount_by_category.items()))
    positive = list(filter(lambda y: max(y[1]) > 0, cumulated))
    negative = list(filter(lambda y: max(y[1]) <= 0, cumulated))

    ax_pos.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax_neg.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    if (len(positive) > 0 and len(negative) > 0):
        ax_pos.yaxis.set_major_formatter('{x} €')
        ax_neg.yaxis.set_major_formatter('{x} €')
        ax_pos.stackplot(dates, list(map(lambda y: y[1], positive)),
                         labels=list(map(lambda y: y[0], positive)))
        ax_neg.stackplot(dates, list(map(lambda y: invert(y[1]), negative)),
                         labels=list(map(lambda y: y[0], negative)))
        ax_neg.legend(loc="upper left")
        render_ax(ax_pos, title="Profit ~ " + title)
        render_ax(ax_neg, title="Loss ~ " + title)

    elif (len(negative) > 0):
        ax_neg.yaxis.set_major_formatter('{x} €')
        ax_neg.stackplot(dates, list(map(lambda y: invert(y[1]), negative)),
                         labels=list(map(lambda y: y[0], negative)))
        ax_neg.legend(loc="upper left")
        render_ax(ax_neg)

    elif (len(positive) > 0):
        ax_pos.yaxis.set_major_formatter('{x} €')
        ax_pos.stackplot(dates, list(map(lambda y: y[1], positive)),
                         labels=list(map(lambda y: y[0], positive)))
        ax_pos.legend(loc="upper left")
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
        ax.legend(loc="upper left")

        render_ax(ax)

    elif (len(positive) > 0 and sum(positive_values) > 0):
        ax.pie(positive_values, labels=positive_labels,
               radius=1,
               wedgeprops=dict(width=0.5, edgecolor="w"),
               autopct="%1.1f%%"
               )
        ax.legend(loc="upper left")
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


def render_synthesis(export_account, dates):
    start = dates[0]
    end = dates[-1]
    with PdfPages(f"{start.isoformat()}_{end.isoformat()}_{days}_days_account_synthesis.pdf") as pdf:
        fig, ax = plt.subplots(4, 1, sharex=True)

        plot_cash_flow(ax[0], ax[1], export_account, dates)

        amount_by_category = export_account.by_category()
        amount_by_sub_category = export_account.by_sub_category()
        plot_repartition(ax[2], ax[3], amount_by_category, dates)
        # for category, amounts in amount_by_sub_category.items():
        #     render_repartition(amounts, dates, title=f"Repartition ~ {category}")

        render_fig(fig, title="Account synthesis", date=end, pdf=pdf)

        fig, ax = plt.subplots(2, 1)
        plot_pie_repartition(ax[0], amount_by_category, dates)
        plot_bar_repartition(ax[1], amount_by_category, dates)

        render_fig(fig, title="Overall repartition", pdf=pdf)

        for category, amounts in amount_by_sub_category.items():
            fig, ax = plt.subplots(3, 1)
            plot_pie_repartition(ax[0], amounts, dates)
            plot_bar_repartition(ax[1], amounts, dates)
            plot_repartition(ax[2], ax[2], amounts, dates)

            render_fig(
                fig, title=f"Detailed Repartition ~ {category}", pdf=pdf)


import_account = Account.parse_import(read_xls_file(IMPORT_FILE))
current_account = Account.parse_current(read_csv_file(CURRENT_DATA))
export_account = current_account.merge(import_account)

write_csv_file(EXPORT_FILE, export_account.to_export())

# datetime.datetime.now().date()
end_date = export_account.ended_at()
# end_date - datetime.timedelta(days=30)
start_date = export_account.started_at()
days = 1
dates = make_linear_date(start_date, end_date, days)

render_synthesis(export_account, dates)

month_scale = make_linear_date(start_date, end_date, 30)
for start, end in zip(month_scale, month_scale[1:]):
    dates = make_linear_date(start, end, days)
    render_synthesis(export_account, dates)
