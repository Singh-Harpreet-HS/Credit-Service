from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import User, Loan, Payment, Billing, DuePayment
from .tasks import calculate_credit_score
from django.utils.dateparse import parse_date
from datetime import datetime
from decimal import Decimal
from rest_framework import status
from django.utils import timezone
from django.http import JsonResponse
#from .serializers import UserSerializer  # Assuming you have a UserSerializer
import uuid
from django.db import transaction
from django.db.utils import DatabaseError
from bson import Binary, UuidRepresentation
from django.core.exceptions import ObjectDoesNotExist
from .serializers import UserSerializer  # Import UserSerializer


@api_view(['POST'])
def register_user(request):
    name = request.data.get('name')
    email = request.data.get('email')
    annual_income = request.data.get('annual_income')
    aadhar_id = request.data.get('aadhar_id')
    
    # Explicitly create UUID in a compatible format
    user_id = Binary.from_uuid(uuid.uuid4(), UuidRepresentation.STANDARD)
    
    user = User.objects.create(
        user_id=user_id,
        name=name,
        email=email,
        annual_income=annual_income,
        aadhar_id=aadhar_id,
        created_at=timezone.now()  # Use timezone-aware datetime
    )
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(['POST'])
@transaction.atomic
def apply_loan(request):
    user_id = request.data.get('user_id')
    loan_amount_str = request.data.get('loan_amount', '0')
    interest_rate_str = request.data.get('interest_rate', '0')
    term_period_str = request.data.get('term_period', '0')
    disbursement_date_str = request.data.get('disbursement_date', '')

    if not all([user_id, loan_amount_str, interest_rate_str, term_period_str, disbursement_date_str]):
        return Response({'error': 'Missing required fields'}, status=400)

    try:
        loan_amount = Decimal(loan_amount_str)
        interest_rate = Decimal(interest_rate_str)
        term_period = int(term_period_str)
        disbursement_date = parse_date(disbursement_date_str)
    except (ValueError, DecimalException):
        return Response({'error': 'Invalid data format'}, status=400)

    try:
        user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except DatabaseError as e:
        return Response({'error': f'Database error: {str(e)}'}, status=500)

    if user.credit_score < 450:
        return Response({'error': 'Credit score too low'}, status=400)
    
    if user.annual_income < 150000:
        return Response({'error': 'Annual income too low'}, status=400)

    if loan_amount > 5000:
        return Response({'error': 'Loan amount exceeds the limit'}, status=400)

    try:
        with transaction.atomic():
            loan = Loan.objects.create(
                user=user,
                loan_amount=loan_amount,
                principal_balance=loan_amount,
                apr=interest_rate,
                term_period=term_period,
                disbursement_date=disbursement_date
            )

            monthly_rate = interest_rate / Decimal(12)
            emi = (loan_amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_period))

            for i in range(term_period):
                due_date = disbursement_date + timedelta(days=(i+1) * 30)
                DuePayment.objects.create(
                    loan=loan,
                    amount_due=emi,
                    due_date=due_date
                )

        serializer = LoanSerializer(loan)
        return Response(serializer.data, status=201)

    except DatabaseError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Database error occurred")
        return Response({'error': f'Database error: {str(e)}'}, status=500)


    

@api_view(['POST'])
def make_payment(request):
    loan_id = request.data.get('loan_id')
    amount = Decimal(request.data.get('amount'))
    payment_date = datetime.now().date()

    try:
        loan = Loan.objects.get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=400)

    due_payments = DuePayment.objects.filter(loan=loan, amount_paid=0).order_by('due_date')
    if not due_payments.exists():
        return Response({'error': 'No due payments found'}, status=400)

    due_payment = due_payments.first()
    if due_payment.due_date > payment_date:
        return Response({'error': 'Cannot pay before due date'}, status=400)

    if due_payment.amount_due != amount:
        return Response({'error': 'Incorrect payment amount'}, status=400)

    due_payment.amount_paid = amount
    due_payment.save()
    loan.principal_balance -= amount
    loan.save()

    Payment.objects.create(
        loan=loan,
        amount=amount,
        payment_date=datetime.now()
    )

    return Response({'message': 'Payment made successfully'}, status=200)

@api_view(['GET'])
def get_statement(request):
    loan_id = request.query_params.get('loan_id')
    
    try:
        loan = Loan.objects.get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=400)

    past_transactions = Payment.objects.filter(loan=loan).values('payment_date', 'amount')
    upcoming_emis = DuePayment.objects.filter(loan=loan, amount_paid=0).values('due_date', 'amount_due')

    return Response({
        'past_transactions': past_transactions,
        'upcoming_transactions': upcoming_emis
    }, status=200)

@api_view(['POST'])
def disburse_money(request):
    user_id = request.data.get('unique_user_id')
    amount = Decimal(request.data.get('amount'))
    disbursement_date = parse_date(request.data.get('disbursement_date'))

    try:
        user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=400)

    # Add logic to ensure the user is eligible for disbursement (if needed)
    # Example: Check if the user meets certain criteria before disbursing money

    # Perform the actual disbursement (for demonstration, we'll just print the details)
    print(f"Disbursing {amount} to user {user.name} ({user.email}) on {disbursement_date}")

    # You can add more complex logic here, such as updating the user's balance, creating payment records, etc.

    return Response({'message': 'Money disbursed successfully'}, status=200)

@api_view(['POST'])
def repay_money(request):
    # Extract data from the request
    loan_id = request.data.get('loan_id')
    amount = request.data.get('amount')

    # Validate input data
    if not loan_id or not amount:
        return Response({'error': 'Loan ID and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        loan = Loan.objects.get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

    if float(amount) <= 0:
        return Response({'error': 'Invalid amount for repayment'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the loan is already fully paid
    if loan.principal_balance == 0:
        return Response({'message': 'The loan has already been fully repaid'}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate remaining balance after repayment
    remaining_balance = loan.principal_balance - float(amount)
    if remaining_balance < 0:
        return Response({'error': 'The repayment amount exceeds the remaining balance'}, status=status.HTTP_400_BAD_REQUEST)

    # Update the loan balance
    loan.principal_balance = remaining_balance
    loan.save()

    # Record the repayment transaction
    Payment.objects.create(loan=loan, amount=amount)

    return Response({'message': 'Repayment successful'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def generate_bill(request):
    user_id = request.data.get('user_id')

    try:
        user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=400)

    loans = Loan.objects.filter(user=user, principal_balance__gt=0)
    if not loans.exists():
        return Response({'message': 'No pending loans for this user'}, status=200)

    # Calculate total outstanding balance
    total_balance = sum(loan.principal_balance for loan in loans)

    # Generate a bill for the user
    bill_date = datetime.now().date()
    due_date = bill_date + timedelta(days=30)  # Assuming 30 days billing cycle
    min_due = total_balance * 0.05  # Minimum due amount (5% of total balance)

    # Create a billing entry for the user
    billing = Billing.objects.create(
        user=user,
        min_due=min_due,
        bill_date=bill_date,
        due_date=due_date
    )

    return Response({'message': 'Bill generated successfully', 'billing_id': billing.billing_id}, status=200)

