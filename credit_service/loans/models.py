from djongo import models
from datetime import datetime, timedelta
from django.utils import timezone  # Add this import
import uuid

class User(models.Model):
     user_id = models.BinaryField(primary_key=True, default=uuid.uuid4)
     name = models.CharField(max_length=255)
     email = models.EmailField(unique=True)
     annual_income = models.DecimalField(max_digits=10, decimal_places=2)
     credit_score = models.IntegerField(default=0)
     created_at = models.DateTimeField(default=timezone.now)
     aadhar_id = models.CharField(max_length=12, unique=True)  # Add this line

     def save(self, *args, **kwargs):
        if isinstance(self.user_id, uuid.UUID):
            self.user_id = Binary.from_uuid(self.user_id, UuidRepresentation.STANDARD)
        if isinstance(self.annual_income, float):
            self.annual_income = Decimal128(str(self.annual_income))
        super().save(*args, **kwargs)

     class Meta:
        app_label = 'loans'

     def __str__(self):
        return self.name

class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    principal_balance = models.DecimalField(max_digits=10, decimal_places=2)
    apr = models.DecimalField(max_digits=5, decimal_places=2)
    term_period = models.IntegerField()  # in months
    disbursement_date = models.DateField()
    created_at = models.DateTimeField(default=datetime.now)

    class Meta:
        app_label = 'loans'

    def __str__(self):
        return f"Loan {self.loan_id} for {self.user.name}"

class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=datetime.now)

    class Meta:
        app_label = 'loans'

    def __str__(self):
        return f"Payment {self.payment_id} for Loan {self.loan.loan_id}"

class Billing(models.Model):
    billing_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    min_due = models.DecimalField(max_digits=10, decimal_places=2)
    bill_date = models.DateField()
    due_date = models.DateField()
    paid = models.BooleanField(default=False)

    class Meta:
        app_label = 'loans'

    def __str__(self):
        return f"Billing {self.billing_id} for {self.user.name}"

class DuePayment(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        app_label = 'loans'

    def __str__(self):
        return f"Due Payment for Billing {self.billing.billing_id}"