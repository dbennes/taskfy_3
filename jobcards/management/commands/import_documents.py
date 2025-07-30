import os
import pandas as pd
from django.core.management.base import BaseCommand
from jobcards.models import DocumentoControle, DocumentoRevisaoAlterada, EngineeringBase

EXCEL_PATH = '00 - Documents E-CLIC/EARLY_ENGINEERING.xlsx'

class Command(BaseCommand):
    help = 'Importa documentos do Excel EARLY_ENGINEERING.xlsx, detecta alterações de revisão e mantém EngineeringBase sincronizada'

    def handle(self, *args, **kwargs):
        if not os.path.exists(EXCEL_PATH):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {EXCEL_PATH}'))
            return

        df = pd.read_excel(EXCEL_PATH)
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

        alteracoes = []
        codigos_validos = set(c.strip().upper() for c in EngineeringBase.objects.values_list('document', flat=True))

        for _, row in df.iterrows():
            codigo_secundario = (row.get('codigo', '') or row.get('codigo_secundario', '')).strip().upper()
            nome_projeto = row.get('nome_do_projeto', '')
            revisao_excel = str(row.get('revisao', '')).strip()

            if not codigo_secundario or codigo_secundario not in codigos_validos:
                continue

            filtro = {'codigo': codigo_secundario, 'nome_projeto': nome_projeto}
            obj, created = DocumentoControle.objects.get_or_create(**filtro)
            revisao_banco = (obj.revisao or '').strip()

            if created:
                DocumentoRevisaoAlterada.objects.create(
                    codigo=codigo_secundario,
                    nome_projeto=nome_projeto,
                    revisao_anterior=None,
                    revisao_nova=revisao_excel,
                )
            elif revisao_banco != revisao_excel:
                DocumentoRevisaoAlterada.objects.create(
                    codigo=codigo_secundario,
                    nome_projeto=nome_projeto,
                    revisao_anterior=revisao_banco,
                    revisao_nova=revisao_excel,
                )
                alteracoes.append({
                    'codigo': codigo_secundario,
                    'nome_projeto': nome_projeto,
                    'revisao_anterior': revisao_banco,
                    'revisao_nova': revisao_excel,
                })

            obj.revisao = revisao_excel
            obj.save()

            # --- Sincronizar a revisao na EngineeringBase ---
            engineering_qs = EngineeringBase.objects.filter(document__iexact=codigo_secundario)
            for eng in engineering_qs:
                rev_antiga = (eng.rev or '').strip()
                if rev_antiga != revisao_excel:
                    # Salva histórico ANTES de atualizar a revisão no banco!
                    DocumentoRevisaoAlterada.objects.create(
                        codigo=codigo_secundario,
                        nome_projeto=nome_projeto,
                        revisao_anterior=rev_antiga,
                        revisao_nova=revisao_excel,
                    )
                    eng.rev = revisao_excel
                    eng.save()
                    print(f'[ENGBASE ALTERADO] {eng.document}: {rev_antiga} → {revisao_excel}')

        self.stdout.write(self.style.SUCCESS(
            f"Importação finalizada. Alterações de revisão: {len(alteracoes)}. EngBase sincronizada!"
        ))
