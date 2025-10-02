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
def get_attr(obj, attr):
    """Retorna o atributo de um objeto, ou None se não existir."""
    return getattr(obj, attr, None)

@register.filter
def get_item(d, key):
    try:
        return d.get(key, [])
    except Exception:
        return []
    


def _to_num(v):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None

@register.filter
def intcomma2(value, dec=2):
    """
    Formata número com separador de milhar e decimais (padrão 2).
    Ex.: 1234567.8 -> 1,234,567.80
    """
    n = _to_num(value)
    if n is None:
        return value
    fmt = f"{{:,.{int(dec)}f}}"
    return fmt.format(n)

@register.filter
def intcomma0(value):
    """Milhar sem casas decimais."""
    n = _to_num(value)
    if n is None:
        return value
    return f"{int(round(n)):,}"