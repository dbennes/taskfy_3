import os
import pandas as pd
from django.db import transaction
from django.core.management.base import BaseCommand
from jobcards.models import DocumentoControle, DocumentoRevisaoAlterada, EngineeringBase

class Command(BaseCommand):
    help = 'Importa documentos do Excel, detecta alterações de revisão e NÃO altera EngineeringBase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='00 - Documents E-CLIC/EARLY_ENGINEERING.xlsx',
            help='Caminho do arquivo Excel'
        )

    def handle(self, *args, **kwargs):
        excel_path = kwargs['file']
        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {excel_path}'))
            return

        df = pd.read_excel(excel_path)
        # normaliza cabeçalhos
        df.rename(
            columns=lambda x: x.strip().lower()
                              .replace(" ", "_")
                              .replace("ç", "c")
                              .replace("ã", "a")
                              .replace("á", "a")
                              .replace("â", "a")
                              .replace("ê", "e")
                              .replace("é", "e")
                              .replace("í", "i")
                              .replace("ó", "o")
                              .replace("ú", "u")
                              .replace("-", "_"),
            inplace=True
        )

        # ainda uso a EngineeringBase só como "lista de válidos" (sem atualizar nada)
        codigos_validos = set(
            (c or '').strip().upper()
            for c in EngineeringBase.objects.values_list('document', flat=True)
        )

        alteracoes = 0

        with transaction.atomic():
            for _, row in df.iterrows():
                codigo_secundario = (row.get('codigo', '') or row.get('codigo_secundario', '')).strip().upper()
                if not codigo_secundario:
                    continue

                # opcional: mantenha o filtro por válidos; se não quiser nem consultar a EngBase, remova este if
                if codigos_validos and codigo_secundario not in codigos_validos:
                    continue

                nome_projeto = (row.get('nome_do_projeto') or '').strip()
                revisao_excel = str(row.get('revisao') or '').strip()

                # cria/atualiza DocumentoControle
                obj, created = DocumentoControle.objects.get_or_create(
                    codigo=codigo_secundario,
                    nome_projeto=nome_projeto,
                    defaults={'revisao': revisao_excel}
                )

                if created:
                    DocumentoRevisaoAlterada.objects.create(
                        codigo=codigo_secundario,
                        nome_projeto=nome_projeto,
                        revisao_anterior=None,
                        revisao_nova=revisao_excel,
                    )
                    alteracoes += 1
                else:
                    revisao_banco = (obj.revisao or '').strip()
                    if revisao_banco != revisao_excel:
                        DocumentoRevisaoAlterada.objects.create(
                            codigo=codigo_secundario,
                            nome_projeto=nome_projeto,
                            revisao_anterior=revisao_banco,
                            revisao_nova=revisao_excel,
                        )
                        obj.revisao = revisao_excel
                        obj.save(update_fields=['revisao'])
                        alteracoes += 1

                # >>> NÃO sincroniza EngineeringBase <<<
                # (removido o bloco que fazia:
                #  for eng in EngineeringBase.objects.filter(document__iexact=codigo_secundario): ...)

        self.stdout.write(self.style.SUCCESS(
            f"Importação finalizada. Alterações de revisão: {alteracoes}. EngineeringBase NÃO foi alterada."
        ))
