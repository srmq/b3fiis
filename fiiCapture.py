import asyncio
from typing import List
import locale
import datetime
import json
import os
import re

from playwright.async_api import async_playwright
from playwright.async_api import expect

OUT_FILE = "b3FIIs.json"
IGNORE_FILE = "ignored.json"

def fiiText2Dict(pageId: str, fiiTokens: List[str]):
    result = {}
    i = 0
    assert fiiTokens[i] == 'Dados'
    i += 1
    assert fiiTokens[i] == 'Nome do Pregão'
    i += 1
    result['Id'] = pageId
    result['Nome'] = fiiTokens[i].strip()
    i += 1
    if fiiTokens[i] != 'Código de Negociação':
        print(f"Warn: No ticker symbol for {result['Nome']}, returning empty")
        return {}
    i += 1
    result['Ticker'] = fiiTokens[i].strip()
    i += 1
    assert fiiTokens[i] == 'CNPJ'
    i += 1
    result['CNPJ'] = fiiTokens[i].strip()
    i += 1
    if fiiTokens[i] == 'Site':
        i += 1
        result['Site'] = fiiTokens[i].strip()
        i += 1
    else:
        result['Site'] = ''
    assert fiiTokens[i] == 'Classificação Setorial'
    i += 1
    result['Setor'] = fiiTokens[i].strip()
    i += 1
    assert fiiTokens[i] == 'Quantidade de Cotas Emitidas'
    i += 1
    cotaData = fiiTokens[i].strip().split("-")
    numStr = cotaData[0].strip()
    numCotas = locale.atoi(numStr)
    result['NumCotas'] = numCotas
    dtEmissao = datetime.datetime.strptime(cotaData[1].strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    result['DtEmissao'] = dtEmissao

    return result

async def main():

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    if  os.path.isfile(OUT_FILE):
        with open(OUT_FILE, 'r') as file:
            fiiDataDicts = json.load(file)
        initialSeenList = [x['Id'] for x in fiiDataDicts]
        alreadySeen = set(initialSeenList)
        del initialSeenList
    else:
        alreadySeen = set()
        fiiDataDicts = []
    
    if os.path.isfile(IGNORE_FILE):
        with open(IGNORE_FILE, 'r') as ignFile:
            ignored = set(json.load(ignFile))
            alreadySeen = alreadySeen.union(ignored)
    else:
        ignored = set()


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        page = await browser.new_page()
        await page.goto("https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/fundos-de-investimentos/fii/fiis-listados/")
        print(await page.title())
        await page.locator("#onetrust-accept-btn-handler").click()
        locator = page.locator("#bvmf_iframe")
        frameLocator = locator.frame_locator(":scope")
        done = False
        numberDone = 0

        while not done:
            cardTitles = await frameLocator.locator('xpath=//div[@class="card-body"]/h5[@class="card-title2"]').all()
            processedCard = False
            for cardTittle in cardTitles:
                name = await cardTittle.all_inner_texts()
                if (len(name) == 0):
                    continue
                name = name[0].strip()
                if name in alreadySeen:
                    continue
                alreadySeen.add(name)
                await cardTittle.click()
                await expect(frameLocator.get_by_text(re.compile("^Dados"))).to_be_visible(timeout=30000)
                locator = frameLocator.locator('xpath=//div[contains(h5/text(), "Dados")]')
                fiiTextData = await locator.all_inner_texts()
                fiiTextData = fiiTextData[0]
                fiiTextData = fiiTextData.replace("\n\n", "\n")
                fiiTextData = fiiTextData.replace("\xa0", "")
                print(fiiTextData)
                splittedText = fiiTextData.split(sep='\n')
                splittedText = [x for x in splittedText if x != '']

                fiiInfo = fiiText2Dict(name, splittedText)
                if fiiInfo:
                    fiiDataDicts.append(fiiInfo)
                    numberDone += 1
                    if numberDone % 2 == 0:
                        print("Writing checkpoint json")
                        with open(OUT_FILE, "w") as outfile:
                            json.dump(fiiDataDicts, outfile)
                else:
                    ignored.add(name)
                    with open(IGNORE_FILE, "w") as ignoreFile:
                        json.dump(list(ignored), ignoreFile)


                
                voltarButton = frameLocator.get_by_role("button", name='VOLTAR')
                await expect(voltarButton).to_be_visible(timeout=30000)
                await voltarButton.click()
                while (await voltarButton.count() > 0):
                    await voltarButton.click()
                await expect(frameLocator.get_by_text('Selecione um Fundo desejado')).to_be_visible(timeout=30000)
                processedCard = True

                break
            if not processedCard:
                locatorNext = frameLocator.locator('xpath=//li[@class="pagination-next"]/a')
                if await locatorNext.count() == 0:
                    done = True
                else:
                    await locatorNext.click()

        print("All done, writing final json")
        with open(OUT_FILE, "w") as outfile:
            json.dump(fiiDataDicts, outfile)
        await browser.close()


asyncio.run(main())