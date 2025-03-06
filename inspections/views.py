from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Issue
from properties.models import Unit, Property
from .forms import MaintenanceAssignForm
from core.decorators import tenant_required

@login_required
@tenant_required
def company_issues(request, company_slug):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt problēmu sarakstu.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Base queryset
    issues = Issue.objects.filter(
        company=company
    ).select_related(
        'unit',
        'unit__property',
        'reported_by',
    ).order_by('-created_at')
    
    # Get properties for filter - IZMAINĪTĀ RINDA
    properties = Property.objects.filter(company=company)
    
    # Apply filters
    property_id = request.GET.get('property')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    issue_type = request.GET.get('type')
    
    if property_id:
        issues = issues.filter(unit__property_id=property_id)
        # Get units for selected property
        units = Unit.objects.filter(property_id=property_id, company=company)
        unit_id = request.GET.get('unit')
        if unit_id:
            issues = issues.filter(unit_id=unit_id)
    else:
        units = None
        
    if status:
        issues = issues.filter(status=status)
    if priority:
        issues = issues.filter(priority=priority)
    if issue_type:
        issues = issues.filter(issue_type=issue_type)
        
    # Pagination
    paginator = Paginator(issues, 20)
    page = request.GET.get('page')
    issues = paginator.get_page(page)
    
    return render(request, 'inspections/company_issues.html', {
        'issues': issues,
        'company': company,
        'properties': properties,
        'units': units,
        'filters': {
            'property_id': property_id,
            'unit_id': unit_id if 'unit_id' in locals() else None,
            'status': status,
            'priority': priority,
            'type': issue_type
        },
        'active_page': 'issues'
    })

@login_required
@tenant_required
def issue_detail(request, company_slug, pk):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību skatīt problēmas detaļas.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    # Get issue with all related data
    issue = get_object_or_404(Issue.objects.select_related(
        'unit',
        'unit__property',
        'reported_by',
        'resolved_by'
    ), id=pk, company=company)
    
    return render(request, 'inspections/issue_detail.html', {
        'issue': issue,
        'company': company,
        'active_page': 'issues'
    })

@login_required
@tenant_required
def update_issue_status(request, company_slug, pk):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību mainīt problēmas statusu.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    issue = get_object_or_404(Issue, id=pk, company=company)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status == 'in_progress':
            # Pāradresējam uz maintenance assign formu
            return redirect('inspections:assign_maintenance', company_slug=company_slug, pk=pk)
            
        elif new_status in ['resolved', 'closed']:
            issue.status = new_status
            issue.resolved_by = request.user
            issue.resolved_date = timezone.now()
            issue.save()
            
            # Ja ir saistīts maintenance ieraksts, atjauninām arī to
            maintenance = issue.maintenance_records.first()
            if maintenance:
                maintenance.status = 'completed'
                maintenance.completed_date = timezone.now()
                maintenance.save()
            
            messages.success(request, f'Problēma atzīmēta kā {issue.get_status_display()}')
            
    return redirect('inspections:issue_detail', company_slug=company_slug, pk=pk)

@login_required
@tenant_required
def assign_maintenance(request, company_slug, pk):
    company = request.tenant
    
    # Pārbaudam vai lietotājam ir tiesības
    if not (request.user == company.owner or request.user.company_memberships.filter(
            company=company, role__in=['ADMIN', 'MANAGER']).exists()):
        messages.error(request, "Jums nav tiesību piešķirt uzdevumus.")
        return redirect('companies_tenant:company_detail', company_slug=company_slug)
    
    issue = get_object_or_404(Issue, id=pk, company=company)
    
    if request.method == 'POST':
        form = MaintenanceAssignForm(request.POST, company=company)  # Padodam company
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.issue = issue
            maintenance.company = company
            maintenance.status = 'scheduled'
            maintenance.save()
            
            # Atjauninām issue statusu
            issue.status = 'assigned'
            issue.save()
            
            messages.success(request, 'Remonta uzdevums veiksmīgi piešķirts.')
            return redirect('inspections:issue_detail', company_slug=company_slug, pk=pk)
    else:
        # Priekšaizpildām description ar issue info
        initial_description = f"Problēmas tips: {issue.get_issue_type_display()}\n"
        initial_description += f"Problēmas apraksts: {issue.description}\n"
        form = MaintenanceAssignForm(company=company, initial={'description': initial_description})  # Padodam company
    
    return render(request, 'inspections/assign_maintenance.html', {
        'form': form,
        'issue': issue,
        'company': company,
        'active_page': 'issues'
    })