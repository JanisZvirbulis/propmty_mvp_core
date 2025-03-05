from django.http import Http404
from companies.models import Company, CompanyMember

# class TenantMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         company_slug = None
        
#         # Mēģinam iegūt company_slug no URL
#         url_parts = request.path_info.split('/')
#         if len(url_parts) > 1 and url_parts[1]:
#             company_slug = url_parts[1]
        
#         if company_slug:
#             try:
#                 request.tenant = Company.objects.get(slug=company_slug)
                
#                 # Pārbaudam vai lietotājs ir pieteicies un ir saistīts ar šo company
#                 if request.user.is_authenticated:
#                     is_member = CompanyMember.objects.filter(
#                         company=request.tenant,
#                         user=request.user
#                     ).exists() or request.tenant.owner == request.user
                    
#                     if not is_member and not request.user.is_superuser:
#                         raise Http404("You don't have access to this company")
#                 else:
#                     # Ja nav pieteicies, redirekto uz login
#                     # Šo daļu var implementēt dažādi
#                     pass
#             except Company.DoesNotExist:
#                 request.tenant = None
#         else:
#             request.tenant = None
        
#         response = self.get_response(request)
#         return response

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company_slug = None
        
        # Mēģinam iegūt company_slug no URL
        url_parts = request.path_info.split('/')
        if len(url_parts) > 1 and url_parts[1]:
            company_slug = url_parts[1]
        
        if company_slug:
            try:
                request.tenant = Company.objects.get(slug=company_slug)
                
                # Pārbaudam vai lietotājs ir pieteicies un ir saistīts ar šo company
                if request.user.is_authenticated:
                    # Inicializējam noklusējuma vērtības
                    request.is_company_owner = request.tenant.owner == request.user
                    request.company_role = None
                    request.is_company_admin = False
                    request.is_company_manager = False
                    request.is_company_member = False
                    
                    # Pārbaudam, vai ir īpašnieks
                    if request.is_company_owner:
                        request.is_company_member = True
                    else:
                        # Mēģinam atrast lietotāja dalībnieka ierakstu
                        try:
                            company_member = CompanyMember.objects.get(
                                company=request.tenant,
                                user=request.user
                            )
                            # Saglabājam lomu un iestatām karogus
                            request.company_role = company_member.role
                            request.is_company_member = True
                            request.is_company_admin = company_member.role == 'ADMIN'
                            request.is_company_manager = company_member.role == 'MANAGER'
                        except CompanyMember.DoesNotExist:
                            # Nav dalībnieks un nav īpašnieks
                            if not request.user.is_superuser:
                                raise Http404("You don't have access to this company")
                else:
                    # Ja nav pieteicies, redirekto uz login
                    # Šo daļu var implementēt dažādi
                    pass
            except Company.DoesNotExist:
                request.tenant = None
        else:
            request.tenant = None
        
        response = self.get_response(request)
        return response
    
class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Izpildās pirms skata
        
        # Ja ir aktīvs tenant un lietotājs ir pieteicies
        if hasattr(request, 'tenant') and request.tenant and request.user.is_authenticated:
            subscription = request.tenant.get_subscription()
            
            # Pievienojam abonementu request objektam, lai vieglāk piekļūt skatos
            request.subscription = subscription
            
            # Pievienojam dažas izmantotas metodes
            request.can_use_invoicing = subscription and subscription.is_active() and subscription.plan.enable_invoicing
            # ... citas pārbaudes
        
        response = self.get_response(request)
        return response