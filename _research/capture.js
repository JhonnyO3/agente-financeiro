// Script de captura visual do site Baseflow
const { chromium } = require('playwright-chromium');
const path = require('path');
const fs = require('fs');

const URL = 'https://baseflow.webflow.io/';
const OUT = path.join(__dirname, 'screenshots');

async function capture() {
  const browser = await chromium.launch({ headless: true });

  // --- DESKTOP 1440px ---
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const pageD = await desktop.newPage();
  console.log('Navigating (desktop)...');
  await pageD.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await pageD.waitForTimeout(3000); // aguarda lazy-load / animações

  // Full-page desktop
  await pageD.screenshot({ path: path.join(OUT, '01_desktop_fullpage.png'), fullPage: true });
  console.log('✓ desktop fullpage');

  // Altura total para dividir em seções
  const totalHeight = await pageD.evaluate(() => document.body.scrollHeight);
  const viewH = 900;
  const sections = Math.ceil(totalHeight / viewH);

  for (let i = 0; i < sections; i++) {
    await pageD.evaluate((y) => window.scrollTo(0, y), i * viewH);
    await pageD.waitForTimeout(500);
    await pageD.screenshot({ path: path.join(OUT, `02_desktop_sec${String(i+1).padStart(2,'0')}.png`) });
    console.log(`✓ desktop section ${i+1}/${sections}`);
  }

  await desktop.close();

  // --- MOBILE 390px ---
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
  });
  const pageM = await mobile.newPage();
  console.log('Navigating (mobile)...');
  await pageM.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await pageM.waitForTimeout(3000);

  await pageM.screenshot({ path: path.join(OUT, '03_mobile_fullpage.png'), fullPage: true });
  console.log('✓ mobile fullpage');

  const totalHeightM = await pageM.evaluate(() => document.body.scrollHeight);
  const viewHM = 844;
  const sectionsM = Math.ceil(totalHeightM / viewHM);

  for (let i = 0; i < sectionsM; i++) {
    await pageM.evaluate((y) => window.scrollTo(0, y), i * viewHM);
    await pageM.waitForTimeout(500);
    await pageM.screenshot({ path: path.join(OUT, `04_mobile_sec${String(i+1).padStart(2,'0')}.png`) });
    console.log(`✓ mobile section ${i+1}/${sectionsM}`);
  }

  await mobile.close();
  await browser.close();
  console.log('\nCaptura concluída!');
}

capture().catch(console.error);
