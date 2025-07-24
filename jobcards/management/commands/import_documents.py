import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from jobcards.models import DocumentoControle, DocumentoRevisaoAlterada, EngineeringBase

EXCEL_PATH = '00 - Documents E-CLIC/EARLY_ENGINEERING.xlsx'  # Caminho relativo ou absoluto conforme seu projeto

class Command(BaseCommand):
    help = 'Importa documentos do Excel EARLY_ENGINEERING.xlsx e detecta alterações de revisão'

    def handle(self, *args, **kwargs):
        # 1. Checa se o arquivo existe
        if not os.path.exists(EXCEL_PATH):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {EXCEL_PATH}'))
            return

        # 2. Lê o Excel e normaliza os nomes das colunas
        df = pd.read_excel(EXCEL_PATH)
        df.rename(
            columns=lambda x: x.strip()
                              .lower()
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

        # 3. Colete todos os documentos válidos na EngineeringBase (códigos secundários)
        codigos_validos = set(
            EngineeringBase.objects.values_list('document', flat=True)
        )

        # 4. Itera sobre as linhas do DataFrame
        for _, row in df.iterrows():
            codigo_secundario = row.get('codigo_secundario', '')
            nome_projeto = row.get('nome_do_projeto', '')
            revisao = row.get('revisao', '')

            if not codigo_secundario or codigo_secundario not in codigos_validos:
                continue

            filtro = {'codigo': codigo_secundario, 'nome_projeto': nome_projeto}
            obj, created = DocumentoControle.objects.get_or_create(**filtro)
            revisao_anterior = obj.revisao

            # NOVO: Só registra alteração se NÃO for a primeira vez (created == False)
            if not created and obj.revisao != revisao:
                DocumentoRevisaoAlterada.objects.create(
                    codigo=codigo_secundario,
                    nome_projeto=nome_projeto,
                    revisao_anterior=revisao_anterior,
                    revisao_nova=revisao,
                )
                alteracoes.append({
                    'codigo': codigo_secundario,
                    'nome_projeto': nome_projeto,
                    'revisao_anterior': revisao_anterior,
                    'revisao_nova': revisao,
                })

            obj.revisao = revisao
            obj.save()  


        # 6. Mensagem final no terminal
        self.stdout.write(self.style.SUCCESS(f"Importação finalizada. Alterações de revisão: {len(alteracoes)}"))
