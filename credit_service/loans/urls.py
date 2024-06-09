from django.urls import path
from .views import disburse_money, repay_money, generate_bill, register_user, apply_loan, make_payment, get_statement

urlpatterns = [
    path('register-user/', register_user, name='register_user'),
    path('apply-loan/', apply_loan, name='apply_loan'),
    path('make-payment/', make_payment, name='make_payment'),
    path('get-statement/', get_statement, name='get_statement'),
    path('disburse-money/', disburse_money, name='disburse_money'),
    path('repay-money/', repay_money, name='repay_money'),
    path('generate-bill/', generate_bill, name='generate_bill'),
]
