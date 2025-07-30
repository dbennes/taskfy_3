import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Use headless=True para rodar sem janela
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto("https://westpaq.e-clic.net/")

        # Login
        await page.fill('input[name="LoginUserName"]', 'vitor.pereira')
        await page.fill('input[name="LoginPassword"]', '123456*Uuu')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')

        # Seleciona cliente
        await page.wait_for_selector('#combo_cliente + .chzn-container .chzn-single')
        await page.click('#combo_cliente + .chzn-container .chzn-single')
        await asyncio.sleep(1)
        await page.click('.chzn-container .chzn-results li:has-text("SNEPCO")')

        # Seleciona projeto
        await page.wait_for_selector('#combo_projetos + .chzn-container .chzn-single')
        await page.click('#combo_projetos + .chzn-container .chzn-single')
        await asyncio.sleep(1)
        await page.click('.chzn-container .chzn-results li:has-text("BNO - BONGA NORTH")')

        # Seleciona pasta
        await page.wait_for_selector('span.tree-title:has-text("02-DED")')
        await asyncio.sleep(1)
        await page.click('span.tree-title:has-text("02-DED")')

        # Espera grid carregar (só para garantir)
        await asyncio.sleep(2)

        # Aguarda botão exportar visível e clica aguardando o download
        await page.wait_for_selector('#exportExcel')
        async with page.expect_download() as download_info:
            await page.click('#exportExcel')
        download = await download_info.value

        # === Caminho raiz do projeto ===
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(base_dir)  # volta para a raiz do projeto

        # Pasta principal e pasta de backup
        pasta_principal = os.path.join(base_dir, '00 - Documents E-CLIC')
        pasta_backup = os.path.join(base_dir, '00 - Documents E-CLIC', 'BACKUP_EARLY_ENGINEERING')
        os.makedirs(pasta_principal, exist_ok=True)
        os.makedirs(pasta_backup, exist_ok=True)

        # Nome fixo do arquivo principal
        caminho_arquivo_principal = os.path.join(pasta_principal, 'EARLY_ENGINEERING.xlsx')

        # Nome do arquivo de backup com timestamp
        data_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        caminho_arquivo_backup = os.path.join(pasta_backup, f'EARLY_ENGINEERING_{data_str}.xlsx')

        # Salva o arquivo principal (sempre sobrescreve)
        await download.save_as(caminho_arquivo_principal)
        print(f"Arquivo principal salvo em: {caminho_arquivo_principal}")

        # Copia para o backup
        import shutil
        shutil.copy2(caminho_arquivo_principal, caminho_arquivo_backup)
        print(f"Backup salvo em: {caminho_arquivo_backup}")

        # Encerra o navegador
        await browser.close()

asyncio.run(main())
