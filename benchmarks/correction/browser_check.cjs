const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

async function main() {
  const directory = __dirname;
  const root = path.dirname(directory);
  const types = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.jsonl': 'application/json', '.md': 'text/plain; charset=utf-8' };
  const server = http.createServer((request, response) => {
    let filename = path.resolve(root, '.' + decodeURIComponent(request.url.split('?')[0]));
    if (!filename.startsWith(root + path.sep)) { response.writeHead(403); response.end(); return; }
    try {
      if (fs.statSync(filename).isDirectory()) filename = path.join(filename, 'index.html');
      response.writeHead(200, { 'Content-Type': types[path.extname(filename)] || 'application/octet-stream' });
      response.end(fs.readFileSync(filename));
    } catch { response.writeHead(404); response.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
  const errors = [];
  const widths = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1365, height: 1000 } });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/correction/');
    assert.equal(await page.locator('#task-rows > tr').count(), 5);
    const tasks = JSON.parse(fs.readFileSync(path.join(directory, 'tasks.json'), 'utf8'));
    const evaluation = JSON.parse(fs.readFileSync(path.join(directory, 'opus-50-20261009/analysis.json'), 'utf8'));
    assert.match(await page.locator('#result-count').innerText(), /50 of 200 tasks/);
    assert.deepEqual(await page.locator('#evaluation-metrics strong').allTextContents(), ['48%', '100%', '100%', '100%']);
    assert.equal(await page.locator('#compare-task option').count(), 50);
    let goldBranchesChecked = 0;
    for (const result of evaluation.results) {
      const task = tasks.find(item => item.id === result.id);
      await page.locator('#compare-task').selectOption(result.id);
      assert.deepEqual(JSON.parse(await page.locator('#actual-json').textContent()), result.parsed_output);
      assert.equal(await page.locator('#raw-output').textContent(), result.raw_output);
      assert.equal(await page.locator('#compare-prompt-text').textContent(), task.prompt);
      assert.match(await page.locator('#compare-status').innerText(), new RegExp(result.status.toUpperCase()));
      assert.equal(await page.locator('#gold-picker-label').isVisible(), task.accepted_answers.length > 1);
      assert.equal((await page.request.get(await page.locator('#selected-receipt').getAttribute('href').then(href => origin + '/correction/' + href))).status(), 200);
      for (let index = 0; index < task.accepted_answers.length; index++) {
        if (task.accepted_answers.length > 1) await page.locator('#compare-gold').selectOption(String(index));
        assert.deepEqual(JSON.parse(await page.locator('#expected-json').textContent()), task.accepted_answers[index]);
        goldBranchesChecked++;
      }
      await page.locator('#compare-task').selectOption(result.id);
      assert.match(await page.locator('#first-difference').innerText(), result.strict_pass ? /Every field matches/ : /First difference/);
    }
    for (const [filter, count] of [['pass',24], ['fail',26], ['not-run',150], ['evaluated',50]]) {
      await page.locator('#eval-filter').selectOption(filter);
      assert.match(await page.locator('#result-count').innerText(), new RegExp(`${count} of 200 tasks`));
    }
    await page.locator('#eval-filter').selectOption('all');
    assert.match(await page.locator('#result-count').innerText(), /200 of 200 tasks/);
    await page.locator('#tense').selectOption('Lun');
    assert.match(await page.locator('#result-count').innerText(), /20 of 200 tasks/);
    await page.locator('#tense').selectOption('');
    await page.locator('#error-axis').selectOption('purusha');
    assert.match(await page.locator('#result-count').innerText(), /67 of 200 tasks/);
    await page.locator('#error-axis').selectOption('');
    await page.locator('#answers-filter').selectOption('multiple');
    assert.match(await page.locator('#result-count').innerText(), /78 of 200 tasks/);
    await page.locator('.alternatives > summary').first().click();
    assert(await page.locator('.alternatives').first().getAttribute('open') !== null);
    await page.locator('#answers-filter').selectOption('');
    await page.locator('#next').click();
    assert.equal(await page.locator('#task-rows > tr').first().getAttribute('data-number'), '6');
    await page.locator('#search').fill('200');
    assert.equal(await page.locator('#task-rows > tr').count(), 1);
    assert.equal(await page.locator('#task-rows > tr').getAttribute('data-number'), '200');
    await page.locator('#search').fill('nothing-will-match-this');
    assert(await page.locator('#empty').isVisible());
    await page.locator('#search').fill('');
    await page.locator('#page-size').selectOption('200');
    assert.equal(await page.locator('#task-rows > tr').count(), 200);
    const displayed = await page.locator('#task-rows .prompt-text').allTextContents();
    assert.deepEqual(displayed, tasks.map(task => task.prompt));
    const firstAnswers = await page.locator('#task-rows > tr > td:last-child > .answer-text').allTextContents();
    assert.deepEqual(firstAnswers.map(JSON.parse), tasks.map(task => task.accepted_answers[0]));
    const links = await page.locator('.links a').evaluateAll(elements => elements.map(element => element.href));
    for (const link of links) assert.equal((await page.request.get(link)).status(), 200, link);
    await page.locator('#page-size').selectOption('5');
    for (const theme of ['light', 'dark']) {
      await page.emulateMedia({ colorScheme: theme });
      for (const width of [320, 390, 768, 1365]) {
        await page.setViewportSize({ width, height: 1000 });
        const actual = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
        assert(actual.scroll <= actual.width, JSON.stringify(actual));
        widths.push({ theme, ...actual });
      }
    }
    await page.emulateMedia({ colorScheme: 'light' });
    await page.setViewportSize({ width: 1365, height: 1000 });
    await page.locator('#compare-task').selectOption(evaluation.results.find(result => result.status === 'fail').id);
    await page.locator('#opus-panel').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'preview-evaluation.png') });
    await page.locator('.compare-toolbar').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'preview-comparison.png') });
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.screenshot({ path: path.join(directory, 'preview-comparison-dark.png') });
    await page.emulateMedia({ colorScheme: 'light' });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(directory, 'preview-desktop.png') });
    await page.locator('#task-1').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'preview-task.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(directory, 'preview-mobile.png') });
    await page.locator('.compare-toolbar').scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'preview-comparison-mobile.png') });
    await page.goto(origin + '/report.html#/correction');
    await page.locator('#correction-frame').waitFor();
    const frame = page.frameLocator('#correction-frame');
    await frame.locator('#task-rows > tr').first().waitFor();
    assert(await page.locator('#top').isHidden());
    assert(await page.locator('#correction-route').isVisible());
    await frame.locator('#eval-filter').selectOption('all');
    await frame.locator('#search').fill('200');
    assert.equal(await frame.locator('#task-rows > tr').count(), 1);
    await page.waitForFunction(() => {
      const frameElement = document.querySelector('#correction-frame');
      const expected = Math.ceil(frameElement.contentDocument.body.getBoundingClientRect().height) + 8;
      return frameElement.clientHeight === expected;
    });
    const heightBefore = await page.locator('#correction-frame').evaluate(element => element.clientHeight);
    await page.waitForTimeout(400);
    const heightAfter = await page.locator('#correction-frame').evaluate(element => element.clientHeight);
    assert.equal(heightBefore, heightAfter, 'Iframe height must settle');
    for (const width of [320, 390, 768, 1365]) {
      await page.setViewportSize({ width, height: 1000 });
      const actual = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
      assert(actual.scroll <= actual.width, JSON.stringify(actual));
    }
    await page.locator('.correction-route-links a').first().click();
    await page.waitForFunction(() => document.getElementById('correction-route').hidden);
    assert(await page.locator('#correction-route').isHidden());
    assert(await page.locator('#top').isVisible());
    await page.goto('file://' + path.join(root, 'report.html') + '#/correction');
    await page.frameLocator('#correction-frame').locator('#task-rows > tr').first().waitFor();
    const identifiers = await page.locator('[id]').evaluateAll(elements => elements.map(element => element.id));
    assert.equal(identifiers.length, new Set(identifiers).size);
    assert.deepEqual(errors, []);
    const result = { passed: true, all_200_prompt_and_primary_answer_pairs_match: true, all_50_model_outputs_and_raw_responses_match: true, comparison_gold_branches_checked: goldBranchesChecked, evaluation_metrics_and_filters: true, filters_and_pagination: true, alternate_answers: true, report_hash_route: true, direct_http_route: true, offline_file_route: true, frame_height_stable: true, download_links: links.length, viewport_checks: widths, javascript_errors: errors };
    fs.writeFileSync(path.join(directory, 'browser-check.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result, null, 2));
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
