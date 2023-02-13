import csv
import datetime
import math

import xlrd

DAY_DELTA = datetime.timedelta(days=1)
MONTH_DELTA = datetime.timedelta(days=31)


def read_xls_file(filepath):
    book = xlrd.open_workbook(filepath, encoding_override="cp1252")
    sheet = book.sheet_by_index(0)
    return [sheet.row_values(i) for i in range(0, sheet.nrows)]


def read_csv_file(filepath):
    with open(filepath, newline="", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=";")
        data = list(reader)
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
    for x in array:
        if predicate(x):
            return True
    return False


def partition(array, predicate):
    positives = []
    negatives = []
    for x in array:
        if predicate(x):
            positives.append(x)
        else:
            negatives.append(x)
    return (positives, negatives)


def unzip(zipped):
    return ([z[0] for z in zipped], [z[1] for z in zipped])


def make_linear_date(start: datetime.date, end: datetime.date):
    total_duration = end - start
    delta = DAY_DELTA
    periods = math.ceil(total_duration.days) + 1
    return [start + i * delta for i in range(periods)]


def make_accounting_term_dates(start: datetime.date, end: datetime.date):
    term_start = datetime.date(start.year, start.month, 1)
    month_duration = (end - term_start).days / 30

    delta = MONTH_DELTA
    periods = math.ceil(month_duration) + 1
    shifted_dates = [term_start + i * delta for i in range(periods)]
    return [datetime.date(d.year, d.month, 1) for d in shifted_dates]


def make_accounting_term_date(year: float, month: float):
    return datetime.date(year, month, 1)


def group_by(keys, values):
    grouped = {}
    for key, value in zip(keys, values):
        try:
            grouped[key] += [value]
        except KeyError:
            grouped[key] = [value]

    return grouped


def sample(dates: list, data: dict):
    new_data = {}

    sorted_dates = sorted(data.keys())
    initial_dates = [d for d in sorted_dates if d <= dates[0]]

    try:
        last_known = data[initial_dates[-1]][-1]
    except IndexError:
        last_known = 0.0

    for d in dates:
        try:
            new_data[d] = data[d][-1]
            last_known = new_data[d]
        except KeyError:
            new_data[d] = last_known

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

        for d in date_range[1:-1]:
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


def smooth(period: int, data: list[float]):
    if (period <= 1):
        return data
    half_period = round(period / 2)
    smoothed = [0] * len(data)
    for idx in range(half_period, len(data) - half_period):
        total = sum(data[idx - half_period:idx + half_period])
        smoothed[idx] = total / period

    return smoothed


def invert(data):
    return [-x for x in data]


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

        (initials, transactions) = partition(
            all_transactions, Transaction.is_initial)

        try:
            initial_balance = initials[0].amount
        except IndexError:
            initial_balance = 0.0

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

        initial_date = self.transactions[0].occured_at - DAY_DELTA
        initial = Transaction.make_initial(initial_date, self.initial_balance)
        initial_row = [0, *initial.to_export()]
        enumerated_transactions = enumerate(self.transactions)
        rows = [[t[0] + 1, *t[1].to_export()] for t in enumerated_transactions]
        return [header, initial_row, *rows]

    def merge(self, other):
        if self.imported_at > other.imported_at:
            raise NotImplementedError

        initial_balance = self.initial_balance
        imported_at = other.imported_at
        last_occured_at = self.ended_at()

        old_transactions = [t_self for t_self in self.transactions if not some(
            other.transactions, lambda t_other: t_other.is_same(t_self))]

        updated_transactions = [t_other for t_other in other.transactions if some(
            self.transactions, lambda t_self: t_self.is_same(t_other))]

        new_transactions = [t_other for t_other in other.transactions if t_other.occured_at > last_occured_at and not some(
            self.transactions, lambda t_self: t_self.is_same(t_other))]

        transactions = old_transactions + updated_transactions + new_transactions

        return Account(initial_balance, imported_at, transactions)

    def occured_at(self):
        return [t.occured_at for t in self.transactions]

    def balance(self):
        balance = [0] * (len(self.transactions) + 1)
        balance[0] = self.initial_balance
        for idx, transaction in enumerate(self.transactions):
            balance[idx + 1] = balance[idx] + transaction.amount

        return group_by(self.occured_at(), balance[1:])

    def gain(self):
        return group_by(self.occured_at(), [max(t.amount, 0) for t in self.transactions])

    def loss(self):
        return group_by(self.occured_at(), [max(-t.amount, 0) for t in self.transactions])

    def started_at(self):
        try:
            return self.transactions[0].occured_at
        except IndexError:
            return self.imported_at

    def ended_at(self):
        try:
            return self.transactions[-1].occured_at
        except IndexError:
            return self.imported_at

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
