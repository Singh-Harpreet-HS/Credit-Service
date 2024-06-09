from django.core.management.base import BaseCommand
from loans.models import User, Loan, Billing, DuePayment
from datetime import datetime, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Run the billing process'

    def handle(self, *args, **kwargs):
        users = User.objects.all()
        for user in users:
            billing_date = user.created_at + timedelta(days=30)
            due_date = billing_date + timedelta(days=15)

            total_min_due = Decimal('0.00')
            loans = Loan.objects.filter(user=user)
            for loan in loans:
                days = (datetime.now().date() - loan.disbursement_date).days
                daily_apr = round(loan.apr / Decimal('365'), 3)
                interest = loan.principal_balance * daily_apr * days
                min_due = (loan.principal_balance * Decimal('0.03')) + interest
                total_min_due += min_due

                Billing.objects.create(
                    user=user,
                    min_due=min_due,
                    bill_date=billing_date,
                    due_date=due_date,
                    paid=False
                )

            self.stdout.write(f'Billing created for user {user.name} with total min_due {total_min_due}')
