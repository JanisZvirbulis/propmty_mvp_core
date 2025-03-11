from django import template

register = template.Library()

@register.filter
def filter_by_property(items, unit_id):
    """
    Filtrē elementus pēc īpašuma ID.
    Šis filtrs darbojas ar skaitītājiem un problēmām.
    """
    if not items:
        return []
    
    # Pārbaudam vai items ir saraksts vai queryset
    result = []
    for item in items:
        # Pārbaudam vai elementam ir 'unit' atribūts
        if hasattr(item, 'unit') and hasattr(item.unit, 'id'):
            if str(item.unit.id) == str(unit_id):
                result.append(item)
    
    return result

@register.filter
def filter_by_lease(items, lease_id):
    """
    Filtrē elementus pēc īres līguma ID.
    Šis filtrs darbojas ar rēķiniem.
    """
    if not items:
        return []
    
    # Pārbaudam vai items ir saraksts vai queryset
    result = []
    for item in items:
        # Pārbaudam vai elementam ir 'lease' atribūts
        if hasattr(item, 'lease') and hasattr(item.lease, 'id'):
            if str(item.lease.id) == str(lease_id):
                result.append(item)
    
    return result