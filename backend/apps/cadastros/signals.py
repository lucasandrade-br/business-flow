from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from rest_framework.serializers import ValidationError as RestValidationError

from .models import PlanoConta, Produto
from .services import validar_categorias_folha


@receiver(m2m_changed, sender=Produto.categorias.through)
def validar_vinculos_produto_categoria(sender, instance, action, reverse, pk_set, **kwargs):
    """Protege a regra de uma folha por familia inclusive fora dos endpoints REST."""
    if action != "pre_add" or not pk_set:
        return

    if not reverse:
        atuais = set(instance.categorias.values_list("id_conta", flat=True))
        try:
            validar_categorias_folha(atuais | set(pk_set))
        except RestValidationError as exc:
            raise DjangoValidationError(str(exc.detail)) from exc
        return

    categoria: PlanoConta = instance
    prefixo_raiz = f"{categoria.codigo_ordenacao.split('.')[0]}."
    conflitos = list(
        Produto.objects.filter(
            id_produto__in=pk_set,
            categorias__codigo_ordenacao__startswith=prefixo_raiz,
        )
        .exclude(categorias=categoria)
        .values_list("id_produto", flat=True)
        .distinct()
    )
    if conflitos:
        raise DjangoValidationError(
            "Um produto pode estar vinculado a apenas uma categoria folha por familia. "
            f"Produtos conflitantes: {', '.join(str(item) for item in sorted(conflitos))}."
        )
