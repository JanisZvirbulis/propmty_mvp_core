from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required  
from django.contrib import messages
from .models import SubscriptionPlan, CompanySubscription
from core.decorators import tenant_required

@login_required
def subscription_plans(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    current_plan = None
    if hasattr(request, 'tenant') and request.tenant:
        current_plan = request.tenant.get_subscription()
    
    return render(request, 'subscriptions/plans.html', {
        'plans': plans,
        'current_plan': current_plan
    })

@login_required
@tenant_required
def subscription_checkout(request, company_slug, plan_code):
    company = request.tenant
    
    # Pārbaudam vai lietotājs ir īpašnieks
    if company.owner != request.user:
        messages.error(request, "Tikai uzņēmuma īpašnieks var mainīt abonēšanas plānu")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    try:
        plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, "Izvēlētais plāns nav atrasts")
        return redirect('subscriptions:plans')
    
    # Šeit būtu jāveic maksājuma apstrāde ar maksājumu sistēmu (piemēram, Stripe)
    # Šis ir vienkāršots piemērs
    
    import datetime
    today = datetime.date.today()
    
    # Ja jau ir abonements, to atjaunojam
    try:
        subscription = company.subscription
        subscription.plan = plan
        subscription.start_date = today
        if plan.billing_period == 'monthly':
            subscription.end_date = today + datetime.timedelta(days=30)
        else:
            subscription.end_date = today + datetime.timedelta(days=365)
        subscription.status = 'active'
        subscription.save()
    except:
        # Ja nav abonementa, izveidojam jaunu
        if plan.billing_period == 'monthly':
            end_date = today + datetime.timedelta(days=30)
        else:
            end_date = today + datetime.timedelta(days=365)
        
        CompanySubscription.objects.create(
            company=company,
            plan=plan,
            start_date=today,
            end_date=end_date,
            status='active'
        )
    
    messages.success(request, f"Jūsu uzņēmumam ir aktivizēts {plan.name} plāns")
    return redirect('companies_tenant:company_detail', company_slug=company_slug)