from celery import shared_task
from .models import User
import csv

@shared_task
def calculate_credit_score(user_id, aadhar_id):
    user = User.objects.get(user_id=user_id)
    
    # Simulating the reading of the CSV file for transactions
    transactions = [
        {'aadhar_id': aadhar_id, 'type': 'CREDIT', 'amount': 100000},
        {'aadhar_id': aadhar_id, 'type': 'DEBIT', 'amount': 20000},
        # Add more transactions as needed
    ]
    
    account_balance = sum(t['amount'] if t['type'] == 'CREDIT' else -t['amount'] for t in transactions)
    
    if account_balance >= 1000000:
        credit_score = 900
    elif account_balance <= 10000:
        credit_score = 300
    else:
        credit_score = 300 + (account_balance - 10000) // 15000 * 10

    user.credit_score = int(credit_score)
    user.save()
