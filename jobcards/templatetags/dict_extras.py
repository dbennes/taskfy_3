from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Pega um item do dicionário, retorna lista vazia se não existe."""
    if not d:
        return []
    return d.get(key, [])

@register.filter
def get_item(dictionary, key):
    """Pega um item do dicionário."""
    if not dictionary:
        return ""
    return dictionary.get(key)

@register.filter
def get_mp_by_labor(manpower_list, direct_labor):
    """Encontra o manpower alocado por direct_labor dentro da lista."""
    for mp in manpower_list or []:
        # Ajuste para garantir comparação correta se vier string do banco:
        if str(mp.direct_labor).strip().lower() == str(direct_labor).strip().lower():
            return mp
    return None

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)