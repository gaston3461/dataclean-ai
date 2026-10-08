from playwright.sync_api import sync_playwright
import json
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8502')
parser.add_argument('--output',default='/tmp/dataclean-v2-visual')
parser.add_argument('--chromium',default='/usr/bin/chromium')
args=parser.parse_args()
output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page.goto(args.url)
    page.get_by_role('button',name='Usar dataset ficticio de ejemplo').click()
    page.locator('[data-testid="stPlotlyChart"]').first.wait_for(timeout=30000)
    page.get_by_text('Hallazgos calculados',exact=True).wait_for()
    page.locator('[data-testid=stApp][data-test-script-state=notRunning]').wait_for()
    page.wait_for_timeout(300)
    page.screenshot(path=str(output/'dashboard-light.png'),full_page=True)
    for width in (1440,768,390):
        page.set_viewport_size({'width':width,'height':1000})
        page.wait_for_timeout(500)
        dims=page.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,kpis:[...document.querySelectorAll('.dc-kpi')].slice(0,4).map(e=>({x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width})),charts:[...document.querySelectorAll('[data-testid="stPlotlyChart"]')].map(e=>({x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width}))})''')
        assert dims['scroll'] == width, 'Desbordamiento horizontal de página'
        assert all(c['x'] >= 0 and c['x']+c['width'] <= width+1 for c in dims['charts'])
        if width==390: assert all(abs(c['width']-358)<2 for c in dims['charts'])
        results.append(dims)
        page.screenshot(path=str(output/f'dashboard-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    sidebar=page.locator('[data-testid="stSidebar"]')
    if not sidebar.is_visible(): page.get_by_role('button',name='Open sidebar').click()
    sidebar.get_by_role('combobox').first.click()
    page.get_by_role('option',name='Oscuro',exact=True).click()
    page.wait_for_timeout(1200)
    page.screenshot(path=str(output/'dashboard-dark.png'),full_page=True)
    results.append(page.evaluate('''() => ({theme:getComputedStyle(document.querySelector('.stApp')).backgroundColor,kpi:getComputedStyle(document.querySelector('.dc-kpi')).backgroundColor})'''))
    sidebar.get_by_text('Visualizaciones',exact=True).click()
    page.get_by_text('Visualizaciones automáticas',exact=True).wait_for()
    page.wait_for_timeout(1000)
    page.screenshot(path=str(output/'visualizations-dark.png'),full_page=True)
    title_color=page.locator('.gtitle').first.evaluate('e=>getComputedStyle(e).fill')
    assert title_color == 'rgb(230, 237, 248)', title_color
    assert page.locator('.dc-kpi-value').first.inner_text() == '8', 'El cambio de tema perdió los datos'
    for width in (768,390):
        page.set_viewport_size({'width':width,'height':1000})
        page.wait_for_timeout(500)
        assert page.evaluate('document.documentElement.scrollWidth') == width
        page.screenshot(path=str(output/f'visualizations-dark-{width}.png'),full_page=True)
    other=browser.new_page(viewport={'width':1440,'height':1000})
    other.goto(args.url+'?tema=claro')
    other.get_by_role('button',name='Usar dataset ficticio de ejemplo').click()
    other.locator('.dc-kpi').first.wait_for()
    assert other.locator('.stApp').evaluate('e=>getComputedStyle(e).backgroundColor') == 'rgb(243, 246, 251)', 'Tema global compartido entre usuarios'
    other.close()
    assert page.locator('[data-testid="stException"]').count()==0
    browser.close()
(output/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
