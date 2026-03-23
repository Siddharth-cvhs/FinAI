import csv
files = [
    ('db1_live_transactions.csv','db1_live_transactions_clean.csv'),
    ('db2_transaction_history.csv','db2_transaction_history_clean.csv')
]
for src, dst in files:
    with open(src, newline='', encoding='utf-8') as f_in, open(dst, 'w', newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = [f for f in reader.fieldnames if f != 'Is_Fraud']
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            row.pop('Is_Fraud', None)
            writer.writerow(row)
print('clean files written')
