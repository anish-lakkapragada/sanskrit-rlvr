"""Render the current single-benchmark investigation without submitting requests."""
from html import escape
from misc import vp_goal as runner
from misc import oai_batch_eval as io


def completed_final_tables(result):
    """Render only the complete, fixed paired cohort; source review stays explicit."""
    if result.get('n') != 1800 or not result['numerical']['both_references_complete']:
        raise ValueError('Only the complete paired 1,800-question result may be displayed')
    return _final_tables(result)


def attempted_final_tables(result):
    """Display a fully attempted cohort while explicitly preserving its missing response."""
    missing = result.get('expected_transport_failures', [])
    if (result.get('n') != 1800 or not result['numerical'].get('all_questions_attempted')
            or result['numerical'].get('both_references_complete')
            or len(missing) != 1 or missing[0].get('provider') != 'OpenAI'
            or missing[0].get('index') != 837
            or result.get('state') != 'complete_attempted_pending_independent_source_adjudication'):
        raise ValueError('Infrastructure-aware display requires the exact fully attempted cohort')
    return _final_tables(result, transport_missing=True)


def _final_tables(result, *, transport_missing=False):
    providers = [('Anthropic', 'Opus 5.5'), ('OpenAI', 'GPT-6 Astra')]
    def pct(value):
        return '—' if value is None else f'{100*value:.2f}%'
    def se(value):
        return '—' if value is None else f'{100*value:.2f} pp'
    scores = []
    for provider, label in providers:
        stats = result['primary'][provider]['statistics']
        if not stats['all_results_present'] or stats['fixed_n'] != 1800:
            raise ValueError('Final result has an incomplete model panel')
        canonical = result['canonical'][provider]['statistics']['all_request']
        all_ = stats['all_request']
        scores.append(f'<tr><td>{label}</td><td>{pct(canonical["accuracy"])} '
                      f'({canonical["correct"]}/1,800)</td><td><strong>{pct(all_["accuracy"])}</strong> '
                      f'({all_["correct"]}/1,800)</td><td>{stats["completed_answer"]["n"]:,}/1,800</td>'
                      f'<td>{se(all_["iid_standard_error"])}</td>'
                      f'<td>{se(all_["root_cluster_sandwich_standard_error"])}</td>'
                      f'<td>{len(result["unrecognized_usable_answers"][provider]):,}</td></tr>')
    heading = ('All questions attempted; one Astra transport failure' if transport_missing
               else 'Complete results before source adjudication')
    tables = (f'<h4>{heading}</h4><div class="table-scroll"><table><thead><tr>'
              '<th>Reference</th><th>Canonical score</th><th>Predeclared spelling score</th><th>Usable answers</th>'
              '<th>Item SE</th><th>Family SE</th><th>Initially unmatched answers</th></tr></thead>'
              f'<tbody>{"".join(scores)}</tbody></table></div>'
              '<p class="forward-copy">Both score columns retain all 1,800 questions. The spelling score uses only '
              'the finite policy adopted before submission. Unrecognized usable answers require independent source '
              'adjudication before a grammatical-error claim; any supported correction applies consistently across '
              'affected models and questions. Neither these preliminary scores nor the independent-question SE '
              'alone qualify the benchmark.</p>')
    if transport_missing:
        bounds = result['primary']['OpenAI']['statistics']['missing_answer_accuracy_bounds']
        tables += ('<p class="note"><strong>One Astra request returned a gateway error and was not replayed.</strong> '
                   'Its question remains in the fixed 1,800-item denominator and is not a demonstrated model error. '
                   f'The spelling-score range allowing for missing answers is {pct(bounds[0])}–{pct(bounds[1])}. '
                   'The failure itself adds 0.056 percentage points of uncertainty. The original complete-response '
                   'analysis remains unavailable; this is a separate infrastructure-aware analysis. '
                   'The failed request retains its full cost reservation.</p>')
    opus_stats = result['primary']['Anthropic']['statistics']
    astra_stats = result['primary']['OpenAI']['statistics']
    tables += ('<p class="forward-copy"><strong>Current result: both references score below 90% before source review.</strong> '
               f'Among usable answers, Opus scores {pct(opus_stats["completed_answer"]["accuracy"])} and '
               f'Astra {pct(astra_stats["completed_answer"]["accuracy"])}. '
               f'Opus has {opus_stats["statuses"].get("refused", 0)} recorded refusals; these are kept separate '
               'from grammatical mistakes. The family standard errors remain above one percentage point, '
               'so the earlier precision requirement is not established by the larger question count.</p>')
    if opus_stats['statuses'].get('refused') == 5:
        tables += ('<p class="forward-copy">The raw provider metadata classifies all five Opus refusals as '
                   '<code>cyber</code>, despite the explicit Sanskrit-verbal-root wording. The exact triggering '
                   'phrase is unknown. Giving credit for all five would raise the current Opus score to '
                   '88.11% before linguistic source corrections.</p>')
    components = [('short_adanta_non_aorist', 'Short-adanta Curadi, outside aorist'),
                  ('other_adanta_aorist', 'Other adanta Curadi, aorist'),
                  ('broad_non_curadi', 'Broader controls outside Curadi')]
    rows = []
    for key, label in components:
        groups = [result['primary'][p]['groups']['cell::'+key] for p, _ in providers]
        if groups[0]['n'] != groups[1]['n']:
            raise ValueError('Model composition differs on the paired cohort')
        rows.append(f'<tr><td>{label}</td><td>{groups[0]["n"]:,}</td>' + ''.join(
                    f'<td>{pct(g["all_request_accuracy"])} ({g["correct"]}/{g["n"]})</td>' for g in groups) + '</tr>')
    tables += ('<div class="table-scroll"><table><thead><tr><th>Fixed grammar component</th><th>Questions</th>'
               f'<th>Opus 5.5</th><th>GPT-6 Astra</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    tense_rows = []
    for key in result['primary']['Anthropic']['groups']:
        if not key.startswith('target_lakara::'):
            continue
        groups = [result['primary'][p]['groups'][key] for p, _ in providers]
        tense_rows.append(f'<tr><td>{escape(key.split("::",1)[1])}</td><td>{groups[0]["n"]:,}</td>' + ''.join(
                          f'<td>{pct(g["all_request_accuracy"])}</td>' for g in groups) + '</tr>')
    analysis_link = ('astra-infrastructure-carry-01/analysis.json' if transport_missing else 'analysis.json')
    tables += ('<details><summary>Accuracy across all ten tense and mood categories</summary>'
               '<div class="table-scroll"><table><thead><tr><th>Lakara</th><th>Questions</th>'
               f'<th>Opus 5.5</th><th>GPT-6 Astra</th></tr></thead><tbody>{"".join(tense_rows)}</tbody></table></div></details>'
               f'<p class="forward-copy"><a href="parallel-search-20261007/four_d-90/final1800-64k-01/{analysis_link}">'
               'Full scores, paired comparison, uncertainty and source-review queue</a>.</p>')
    return tables


def source_audit_followup():
    """Render the separate source audit without changing historical result tables."""
    prefix = 'parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01'
    path = runner.ROOT/'benchmarks'/prefix/'source-adjudication/current-audit-summary.json'
    if not path.exists():
        return ''
    audit = io.read_json(path)
    if audit.get('n_per_provider') != 1800 or not audit.get('historical_results_preserved'):
        raise ValueError('Source audit must preserve the complete historical panel')
    layer = audit['applied_source_layer']
    layer_path = runner.ROOT/layer['analysis_path']
    review_path = runner.ROOT/layer['review_path']
    if (io.sha256(layer_path) != layer['analysis_sha256']
            or io.sha256(review_path) != layer['review_sha256']):
        raise ValueError('Source audit application fingerprints changed')
    result, review = io.read_json(layer_path), io.read_json(review_path)
    if not review.get('passed') or review['analysis_sha256'] != layer['analysis_sha256']:
        raise ValueError('Source application must have a passing bound check')
    rows = []
    for provider, label in [('Anthropic', 'Opus 5.5'), ('OpenAI', 'GPT-6 Astra')]:
        stats = result['models'][provider]['statistics']
        score = stats['all_request']
        rows.append(f'<tr><td>{label}</td><td>{score["correct"]:,}/1,800</td>'
                    f'<td>{100*score["accuracy"]:.2f}%</td>'
                    f'<td>{len(result["source_changes"][provider])}</td></tr>')
    analysis_href = layer['analysis_path'].removeprefix('benchmarks/')
    text = ('<h4>Source audit: accepted alternatives and defective inputs</h4>'
            '<p class="forward-copy">This audit checks grammar texts and dictionaries without additional paid '
            'provider calls. Source-backed alternatives apply symmetrically to both models. '
            'The following separate score layer adds valid answers; it does not yet resolve defective inputs.</p>'
            '<div class="table-scroll"><table><thead><tr><th>Reference</th><th>Correct</th>'
            '<th>With adopted alternatives</th><th>Changed grades</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="forward-copy">{escape(audit["applied_source_layer_note"])} '
            f'<a href="{analysis_href}">Separate score layer and exact corrections</a>.</p>')
    if audit.get('input_defect_note'):
        text += ('<p class="note warm"><strong>Input repairs remain necessary.</strong> '
                 f'{escape(audit["input_defect_note"])} '
                 'Old answers are not evidence of performance on repaired prompts. '
                 'No questions have been discarded or replaced to improve the score.</p>')
    text += (f'<p class="forward-copy">{escape(audit["review_progress_note"])} '
             f'<a href="{prefix}/source-adjudication/current-audit-summary.json">Audit accounting and evidence</a> · '
             f'<a href="{prefix}/source-adjudication/input-metadata-audit.md">All-family input audit</a>.</p>'
             '<p class="forward-copy"><strong>Difficulty remains concentrated.</strong> '
             'Five verbal families account for 187 of Opus’s 219 initially noncorrect results; '
             'two account for 128. Those 187 answers have source-supported stem errors. '
             'Coverage of 755 families therefore does not establish equally broad difficulty or '
             'sub-one-point uncertainty on new verbal families.</p>')
    if audit.get('critical_stem_note'):
        text += ('<p class="note warm"><strong>A material source sensitivity:</strong> '
                 f'{escape(audit["critical_stem_note"])} '
                 f'<a href="{prefix}/source-adjudication/critical-stem-followup.md">'
                 'Printed evidence, conflicting transcription and score sensitivity</a>.</p>')
    if audit.get('bounded_accounting'):
        accounting = audit['bounded_accounting']
        accounting_path = runner.ROOT/accounting['path']
        check_path = runner.ROOT/accounting['review_path']
        if (io.sha256(accounting_path) != accounting['sha256']
                or io.sha256(check_path) != accounting['review_sha256']):
            raise ValueError('Bounded source accounting changed after review')
        receipt = io.read_json(check_path)
        if (not receipt.get('passed')
                or receipt.get('bounded_answer_audit_sha256') != accounting['sha256']):
            raise ValueError('Bounded source accounting review did not pass')
        bounded = io.read_json(accounting_path)
        range_rows = []
        for provider, label in [('Anthropic', 'Opus 5.5'), ('OpenAI', 'GPT-6 Astra')]:
            model = bounded['models'][provider]
            low, high = model['audit_accounting_bounds']
            counts = model['counts']
            nonanswers = counts.get('refusal', 0) + counts.get('infrastructure_missing', 0)
            range_rows.append(f'<tr><td>{label}</td><td>{counts["source_rejected"]}</td>'
                              f'<td>6</td><td>{nonanswers}</td>'
                              f'<td>{100*low:.2f}–{100*high:.2f}%</td></tr>')
        text += ('<details><summary>How the six flagged inputs and nonanswers affect the historical score</summary>'
                 '<div class="table-scroll"><table><thead><tr><th>Reference</th><th>Source-supported rejections</th>'
                 '<th>Flagged inputs</th><th>Nonanswers</th><th>Accounting range</th></tr></thead>'
                 f'<tbody>{"".join(range_rows)}</tbody></table></div>'
                 '<p class="forward-copy">These bounds retain all 1,800 questions and give either no credit or '
                 'credit to every flagged input and nonanswer. They assume the unflagged accepted keys and '
                 'bounded source decisions remain valid; they do not cover undiscovered key defects, rerun '
                 'variation, or performance on repaired prompts. Both ranges remain below 90%. '
                 f'<a href="{accounting["path"].removeprefix("benchmarks/")}">Every answer disposition</a> · '
                 f'<a href="{prefix}/source-adjudication/input-repair-previews.json">Three exact repair previews</a>.'
                 '</p></details>')
    return text


def render(analysis):
    state = runner.load()
    fast = analysis.get('acceleration')
    analysis_path = 'parallel-search-20261007/acceleration/analysis.json' if fast else 'parallel-search-20261007/analysis.json'
    def pct(p):
        return '—' if p is None else f'{100*p:.2f}%'
    def result(track, role='primary'):
        value = analysis['tracks'][track]
        if role not in value:
            return 'Awaiting complete panel'
        stats = value[role]['statistics']
        all_, usable = stats['all_request'], stats['completed_answer']
        lo, hi = all_['iid_wilson_95_interval']
        return (f"<strong>{pct(all_['accuracy'])}</strong> ({all_['correct']}/{all_['n']})"
                f"<br><span class='small'>Usable: {pct(usable['accuracy'])}; "
                f"family SE {100*all_['root_cluster_sandwich_standard_error']:.2f} pp"
                f"<br>Nominal Wilson 95%: {pct(lo)}–{pct(hi)}</span>")
    jobs = []
    names = ([j['id'] for t in analysis['tracks'].values() for j in t.get('jobs', [])] if fast else
             ['opus-simple4d-90-01', 'opus-modification-01', 'opus-modification-control-01'])
    received = 0
    for name in names:
        j = state['jobs'].get(name, {})
        counts = j.get('batch', {}).get('request_counts', {})
        if fast:
            count = len(list((runner.OUT/'jobs'/name).glob('task-*.result.json')))
            received += count
            jobs.append(f"<li><code>{name}</code>: {count}/{j.get('n',40)} direct responses; "
                        f"{'settled' if j.get('settled') else 'pending settlement'}</li>")
            continue
        jobs.append(f"<li><code>{name}</code>: {escape(j.get('status', 'not submitted'))}"
                    f"; {counts.get('succeeded', 0)}/200 provider successes</li>")
    budgets = []
    for provider in runner.PROVIDERS:
        settled = state['historical_spend_micro'][provider] + sum(
            j.get('actual_cost_upper_micro', 0) for j in state['jobs'].values()
            if j['provider'] == provider and (j.get('settled') or
               j.get('accounting_driver') == 'continuous-final-64k-v1'))
        budgets.append(f"{provider}: <strong>${settled/1e6:,.2f} known spend</strong>; "
                       f"${runner.committed(state, provider)/1e6:,.2f} including outstanding maximum reservations "
                       f"/ ${runner.PROVIDERS[provider]['cap_micro']/1e6:,.0f} cap")
    paired = analysis['tracks']['modification'].get('paired')
    sensitivity = analysis.get('source_sensitivity')
    source_note = ''
    if sensitivity:
        source_note = ('<p class="forward-copy"><strong>Answer-key review:</strong> one paired item (dictionary entry 10.0400) '
                       'has an unresolved variant-union question carried over from an earlier source audit. It was flagged before outcomes were read. '
                       'The raw 200-question scores stay unchanged; the separate sensitivity uses the same 199 pairs in both arms. '
                       '<a href="parallel-search-20261007/modification-01/review-four-d-agent-source-hold.json">Input-only audit</a>.</p>')
        if sensitivity['state'] == 'complete_supplementary_sensitivity':
            ma = sensitivity['modification']['statistics']['all_request']['accuracy']
            ca = sensitivity['control']['statistics']['all_request']['accuracy']
            source_note += f'<p class="forward-copy">Supplementary 199-pair result: modification {pct(ma)}, creation {pct(ca)}. <a href="{analysis_path if fast else "parallel-search-20261007/source-sensitivity.json"}">Full sensitivity analysis</a>.</p>'
    comparison = 'The paired comparison will appear after both modification and control batches settle.'
    if paired:
        lo, hi = paired['family_bootstrap_95_interval']
        comparison = (f"Modification minus matched creation: <strong>{100*paired['all_request_accuracy_difference']:+.2f} "
                      f"percentage points</strong>; paired family-bootstrap 95% interval "
                      f"{100*lo:+.2f} to {100*hi:+.2f} points. Both arms have identical accepted target answers.")
    findings = ''
    four = analysis['tracks']['four_d'].get('primary')
    if four:
        cells = [('cell::short_adanta_non_aorist', 'Short-adanta verbs, non-aorist'),
                 ('cell::other_adanta_aorist', 'Other adanta verbs, aorist'),
                 ('cell::broad_non_curadi', 'Broader controls')]
        body = ''.join(f'<tr><td>{label}</td><td>{four["groups"][key]["correct"]}/{four["groups"][key]["n"]}</td>'
                       f'<td>{pct(four["groups"][key]["all_request_accuracy"])}</td></tr>' for key,label in cells)
        errors = four['statistics']['fixed_n']-four['statistics']['all_request']['correct']
        lun = four['groups']['target_lakara::Lun']
        non_lun_errors = errors-(lun['n']-lun['correct'])
        tenses = sum(v['correct']<v['n'] for k,v in four['groups'].items() if k.startswith('target_lakara::'))
        findings = (f'<h4>Where the 4D result comes from</h4><div class="table-scroll"><table><thead>'
                    f'<tr><th>Predeclared component</th><th>Correct / questions</th><th>Accuracy</th></tr></thead>'
                    f'<tbody>{body}</tbody></table></div><p class="forward-copy">The {errors} raw misses span '
                    f'{four["wrong_completed_families"]} verbal families and {tenses} tense/mood categories. '
                    f'<strong>{non_lun_errors}/{errors} misses are outside the aorist.</strong> '
                    'This is evidence for a concentrated 4D challenge. It does not establish a broad random-sample score below 90%. '
                    'The family-based standard error remains above the final one-percentage-point requirement.</p>')
    if paired:
        m = analysis['tracks']['modification']['primary']['statistics']['all_request']
        c = analysis['tracks']['modification']['control']['statistics']['all_request']
        if m['accuracy'] >= c['accuracy']:
            findings += ('<p class="note warm"><strong>The modification pilot supplied no measured extra difficulty.</strong> '
                         f'Opus scored {m["correct"]}/{m["n"]} without the dhātu, versus {c["correct"]}/{c["n"]} '
                         'on the matched creation questions. This closes this balanced tense-change pilot as a hardness lead; '
                         'it does not prove that every possible modification task is easy. With all answers correct, a zero empirical '
                         'bootstrap standard error does not establish zero population uncertainty; the Wilson interval is shown above.</p>')
    fast_note = ''
    reviews = ''
    astra_note = ''
    ending_note = ''
    scheduling_note = ''
    continuous_note = ''
    training_note = ''
    scale_note = ''
    larger_note = ''
    scale_path = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/scale-feasibility.json'
    if scale_path.exists():
        scale = io.read_json(scale_path)
        rows = ''
        for n in ['1000', '1250']:
            candidate = scale['candidate_allocations'][n]
            rows += (f'<tr><td>{candidate["n"]:,}</td><td>{candidate["family_count"]}</td>'
                     f'<td>{candidate["cell_quotas"]["short_adanta_non_aorist"]} / 14 families</td>'
                     f'<td>{100*candidate["iid_se_at_forecast"]:.2f} pp</td>'
                     f'<td>{100*candidate["family_mean_transport_se"]:.2f} pp</td></tr>')
        scale_note = ('<h4>Scaling the same composition</h4><p class="forward-copy">An offline dictionary census generated '
                      'valid, fresh-tuple allocation proposals beyond the original task pool. These retain the 52% / 8% / 40% mixture '
                      'and 12% aorist. They have enough unique questions, but the difficult non-aorist component still draws on only '
                      '<strong>14 test families</strong>; its separate RL training supply has nine families. '
                      'The uncertainty estimates below are conditional projections from development evidence, not measured final scores.</p>'
                      '<div class="table-scroll"><table><thead><tr><th>Proposed questions</th><th>Total families</th>'
                      '<th>Hard non-aorist component</th><th>SE if independent</th><th>Family-based projection</th></tr></thead>'
                      f'<tbody>{rows}</tbody></table></div><p class="forward-copy">More forms of the same families do not establish '
                      'the requested precision for performance on new families. A larger set also draws on the future test-family reserve; '
                      'these proposals have not been frozen or evaluated. Regeneration and existing source exclusions are complete, '
                      'but independent source review of every new form is not. Legacy analysis inspected the dictionary before the split, '
                      'so these are not never-inspected verbal families. '
                      '<a href="parallel-search-20261007/four_d-90/scale-feasibility.json">Census, allocations and assumptions</a>.</p>')
        hold_path = scale_path.parent/'test-source-hold-predeclaration.json'
        if hold_path.exists():
            hold = io.read_json(hold_path)
            scale_note += (f'<p class="note warm"><strong>Source review before final selection:</strong> '
                           f'{len(hold["affected_proposed_ids"])} questions in the unscored 1,250-item proposal are now held across three '
                           'families. The issues are an omitted documented variant and unresolved finite-form or ending-set traditions. '
                           'Two further lexical-reading/classification questions require clarification. These findings do not change the '
                           'completed 200-question development panel. The 39-family review checks lexical and representative forms; '
                           'it does not certify every proposed answer union. '
                           '<a href="parallel-search-20261007/four_d-90/test-hard-family-source-review.md">Source audit</a> · '
                           '<a href="parallel-search-20261007/four_d-90/test-source-hold-predeclaration.json">Prospective holds</a>.</p>')
        candidate_path = scale_path.parent/'candidate-1250-source-filtered/manifest.json'
        revision_path = scale_path.parent/'candidate-1250-v2/manifest.json'
        if revision_path.exists():
            candidate_path = revision_path
        if candidate_path.exists():
            candidate = io.read_json(candidate_path)
            candidate_prefix = 'parallel-search-20261007/four_d-90/'+candidate_path.parent.name
            membership = ('The latest revision preserves 1,246 questions from the first source-filtered candidate and replaces '
                          'four questions whose grammatical-group classification was uncertain. Across both revisions, 16 original '
                          'proposed questions have been replaced using outcome-independent rules. The छद reading is retained after '
                          'confirmation in two printed primary sources. '
                          if candidate.get('version') == 2 else
                          'It preserves 1,238 original proposed questions and replaces the 12 source-held questions '
                          'using the same grammar group and outcome-independent balancing. ')
            scale_note += (f'<p class="forward-copy"><strong>A complete 1,250-question candidate now exists:</strong> '
                           f'{candidate["families"]} verbal families, all ten classes and tenses, 12% aorist, '
                           f'and balanced person/number coverage. {membership}'
                           'All 1,250 answers regenerated, and all prompts retain exactly dhātu plus four coordinates. '
                           'This is an <strong>unscored proposal</strong>; it has not been registered for paid evaluation. '
                           'The small difficult-family supply, source-review limits, and final precision requirement remain unresolved. '
                           f'<a href="{candidate_prefix}/manifest.json">Candidate audit and limitations</a> · '
                           f'<a href="{candidate_prefix}/public-prompts.json">All public questions</a> · '
                           f'<a href="{candidate_prefix}/tasks.json">Tasks and canonical answers</a> · '
                           '<a href="parallel-search-20261007/four_d-90/reading-clarification.md">Lexical reading clarification</a>.</p>')
            if (candidate_path.parent/'independent-input-review.json').exists():
                scale_note += ('<p class="forward-copy"><strong>Independent input review passed:</strong> '
                               'the candidate keys and prompts were checked, and replacements follow the source decisions; '
                               'a broader scan of 116 historical input files found zero exact-tuple or current registered-family overlaps. '
                               'Removing gold and campaign metadata leaves the public prompts identical. '
                               'This certifies the checked input mechanics, while final linguistic and performance qualification remain pending. '
                               f'<a href="{candidate_prefix}/independent-input-review.md">Independent checks</a> · '
                               '<a href="parallel-search-20261007/four_d-90/source-hold-supplement.md">Why the three source exclusions remain</a>.</p>')
            if (candidate_path.parent/'scoring-adoption.json').exists():
                scale_note += ('<p class="forward-copy"><strong>Fair spelling policy declared before evaluation:</strong> '
                               'the candidate retains all 2,248 canonical forms and now also recognizes 2,264 documented, '
                               'task-specific spelling alternatives across 829 questions. An independent reviewer checked the unchanged '
                               'phonological rules, task isolation and coverage across all tenses, including periphrastic perfects. '
                               'Canonical, whitelist and later source-adjudicated scores will stay separate. Every usable unrecognized '
                               'answer still requires source review before being counted as a linguistic error; 53 questions have '
                               'explicitly flagged residual spelling contexts. '
                               f'<a href="{candidate_prefix}/scoring-adoption.json">Prospective scoring declaration</a> · '
                               f'<a href="{candidate_prefix}/spelling-policy-proposal/independent-review.md">Independent scoring review</a>.</p>')
    training_path = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/rl-supply/supply-audit.json'
    if training_path.exists():
        training = io.read_json(training_path)
        labels = [('short_adanta_non_aorist','Short-adanta, non-aorist'),
                  ('other_adanta_aorist','Other adanta, aorist'),('broad_non_curadi','Broader controls')]
        rows = ''.join(f'<tr><td>{label}</td><td>{training["main_supply"][key]["families"]}</td>'
                       f'<td>{training["main_supply"][key]["public_tuples"]:,}</td></tr>' for key,label in labels)
        training_note = ('<h4>What can a fresh model train on?</h4><div class="table-scroll"><table><thead>'
                         '<tr><th>Same grammar component</th><th>Training families</th><th>Available questions</th></tr></thead>'
                         f'<tbody>{rows}</tbody></table></div><p class="forward-copy">The declared training split supplies '
                         '<strong>32,454 distinct public questions across 369 families</strong>. A deterministic 1,400-question '
                         'curriculum manifest follows the same 52% / 8% / 40% mix, with 728 / 112 / 560 questions. '
                         'It has no declared-family or exact-question overlap with development or the 1,250-question candidate. '
                         'These are metadata and mechanically derived supply counts; no training has started, and the new reward keys '
                         'have not received full independent source certification. The main difficult component still offers only nine training families.</p>'
                         '<p class="forward-copy"><strong>Separation caveat:</strong> the existing family key includes the conjugation class. '
                         'Ten identical dhātu citations appear across different classes in both training and the candidate, affecting '
                         '11 candidate questions and 22 curriculum questions. Thus declared-family separation does not establish entirely '
                         'unseen Sanskrit lexemes. A stricter training-only exclusion is being assessed; it does not change the test questions. '
                         '<a href="parallel-search-20261007/four_d-90/rl-supply/supply-audit.json">Supply and overlap audit</a> · '
                         '<a href="parallel-search-20261007/four_d-90/rl-supply/curriculum-manifest.json">1,400-question curriculum manifest</a>.</p>')
        if (training_path.parent/'strict-citation-option/curriculum-manifest.json').exists():
            training_note = training_note.replace('A stricter training-only exclusion is being assessed; it does not change the test questions.',
                'A separate stricter training option closes that exact-citation overlap without changing test questions.')
            training_note += ('<p class="note"><strong>Preferred prospective training option:</strong> '
                              'exclude every training entry whose exact dictionary citation occurs anywhere in development or test, '
                              'even in another class. This leaves <strong>29,034 questions across 332 families</strong>, '
                              'preserves all nine short-adanta and 15 other-adanta training families, and still supplies '
                              'a balanced 1,400-question curriculum at 52% / 8% / 40%. It removes 37 broad families and 3,420 questions. '
                              'The resulting inventory has zero raw-citation overlap with the full development/test inventory. '
                              'Different marker spellings, synonymous roots and pretrained-model exposure remain outside this guarantee. '
                              '<a href="parallel-search-20261007/four_d-90/rl-supply/strict-citation-option/README.md">Strict training option and limits</a> · '
                              '<a href="parallel-search-20261007/four_d-90/rl-supply/strict-citation-option/curriculum-manifest.json">Pinned curriculum</a>.</p>')
            export_dir = training_path.parent/'strict-citation-option/materialized-1400'
            if (export_dir/'manifest.json').exists():
                export_prefix = 'parallel-search-20261007/four_d-90/rl-supply/strict-citation-option/materialized-1400'
                training_note += ('<p class="forward-copy"><strong>The 1,400-question curriculum is now exported.</strong> '
                                  'Public prompts and canonical answer unions are separate files, preserving all 56 curriculum blocks '
                                  'and 332 families. Regeneration and overlap checks passed against the full 1,800-question benchmark, '
                                  'including exact raw and rendered citations. No training has started. The optional spelling reward '
                                  'policy is separate and has not been adopted. '
                                  f'<a href="{export_prefix}/README.md">Export and validation limits</a> · '
                                  f'<a href="{export_prefix}/public-tasks.jsonl">Public training questions</a> · '
                                  f'<a href="{export_prefix}/canonical-gold.jsonl">Canonical answer unions</a>.</p>')
                if (export_dir/'independent-review.md').exists():
                    training_note += ('<p class="forward-copy">Independent export and finite-map reviews passed. '
                                      'Future reward integration must handle unfamiliar usable answers pending source review; '
                                      'being outside the finite whitelist is not itself a settled linguistic-error judgment. '
                                      f'<a href="{export_prefix}/independent-review.md">Independent export review</a> · '
                                      f'<a href="{export_prefix}/spelling-policy-proposal/independent-review.md">Spelling review</a>.</p>')
    astra = analysis.get('astra_comparison')
    if astra:
        astra_result = 'Accuracy will appear after all 200 questions settle.'
        if 'astra' in astra:
            stats = astra['astra']['statistics']['all_request']
            opus_stats = astra['opus']['statistics']['all_request']
            lo, hi = astra['paired']['family_bootstrap_95_interval']
            errors = stats['n'] - stats['correct']
            lun = astra['astra']['groups']['target_lakara::Lun']
            non_lun_errors = errors - (lun['n'] - lun['correct'])
            astra_result = (f'<strong>Astra: {pct(stats["accuracy"])} ({stats["correct"]}/{stats["n"]})</strong>; '
                            f'<strong>Opus: {pct(opus_stats["accuracy"])} ({opus_stats["correct"]}/{opus_stats["n"]})</strong>. '
                            'Both observed development scores are below 90%. Astra had no missing answers, refusals or truncations; '
                            f'{non_lun_errors}/{errors} of its misses are outside the aorist. Astra '
                            f'family SE {100*stats["root_cluster_sandwich_standard_error"]:.2f} pp. '
                            f'Paired difference from Opus: {100*astra["paired"]["all_request_accuracy_difference"]:+.2f} percentage points. '
                            f'The family-bootstrap 95% interval is {100*lo:+.2f} to {100*hi:+.2f} points, so this does not establish a reliable model ordering. '
                            'Independent review and final held-out qualification remain separate requirements.')
        astra_note = (f'<h4>Astra comparison on the same 200 creation questions</h4><p class="note">'
                      f'<strong>{astra["received"]}/200 responses received; {astra["settled"]}/200 settled.</strong> '
                      f'{astra_result}<br>Execution: {escape(astra["execution"]["state"].replace("_"," "))}. '
                      'Same model-visible prompt, xHigh, 65,536-token ceiling and accepted answers; direct standard-tier API, '
                      'eight concurrent requests in groups of ten, no paid retries. '
                      f'Upper cost settled: <strong>${astra["cost_upper_usd"]:.2f}</strong>; '
                      f'${astra["committed_usd"]:.2f} including pending maximum reservations. '
                      'The $150 additional ceiling fits within the existing $2,000 OpenAI cap and preserves final-evaluation reserves. '
                      '<a href="parallel-search-20261007/astra-comparison-01/plan.json">Frozen comparison plan</a> · '
                      '<a href="parallel-search-20261007/astra-comparison-01/analysis.json">Live analysis</a>.</p>')
        if 'astra' in astra:
            rows = ''
            for key, label in [('cell::short_adanta_non_aorist', 'Short-adanta, non-aorist'),
                               ('cell::other_adanta_aorist', 'Other adanta, aorist'),
                               ('cell::broad_non_curadi', 'Broader controls')]:
                a, o = astra['astra']['groups'][key], astra['opus']['groups'][key]
                rows += (f'<tr><td>{label}</td><td>{o["correct"]}/{o["n"]} ({pct(o["all_request_accuracy"])})</td>'
                         f'<td>{a["correct"]}/{a["n"]} ({pct(a["all_request_accuracy"])})</td></tr>')
            astra_note += ('<div class="table-scroll"><table><thead><tr><th>Same predeclared component</th>'
                           '<th>Opus 5.5</th><th>GPT-6 Astra</th></tr></thead>'
                           f'<tbody>{rows}</tbody></table></div><p class="forward-copy">'
                           '<strong>Size implication:</strong> at the observed 80.5%, Astra would need at least 1,570 '
                           'independent questions for sampling SE below one percentage point. The earlier 1,250-question '
                           'proposal projects 1.12 pp for Astra and 0.94 pp for Opus under independence alone. '
                           'Related forms introduce additional family dependence; these are projections, not final precision claims.</p>')
        astra_review_path = runner.ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01/independent-result-review.json'
        if astra_review_path.exists():
            review = io.read_json(astra_review_path)
            if review.get('mechanical_protocol_and_grading_review_passed'):
                astra_note += ('<p class="forward-copy"><strong>Independent completed-result review passed:</strong> '
                               'all 200 paired prompts, raw receipts and grades were checked; all 39 Astra misses received '
                               'source dispositions. No submitted licensed alternative or demonstrated key defect requiring '
                               'a score change was identified. The bounded review retains 80.5% / 87.5%; it does not certify '
                               'every possible Sanskrit variant. '
                               '<a href="parallel-search-20261007/astra-comparison-01/independent-result-review.json">Independent audit and per-error evidence</a>.</p>')
    ending = analysis.get('ending_screen')
    if ending:
        ending_dir = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/ending-screen-01'
        execution_link = ('registration.json' if (ending_dir/'registration.json').exists() else 'executor-process.json')
        analysis_link = ('analysis.json' if (ending_dir/'analysis.json').exists() else 'execution.json')
        score = 'Accuracy will appear after all 96 questions settle.'
        if 'primary' in ending:
            primary = ending['primary']['statistics']['all_request']
            canonical = ending['canonical']['statistics']['all_request']
            score = (f'Predeclared spelling-aware accuracy: <strong>{pct(primary["accuracy"])} '
                     f'({primary["correct"]}/{primary["n"]})</strong>; canonical-only accuracy: '
                     f'{pct(canonical["accuracy"])}. Every unrecognized answer still requires independent source review '
                     'before counting it as a linguistic error or deciding whether this hypothesis advances.')
            if primary['accuracy'] >= .9:
                score += (' <strong>This pilot fails its predeclared hardness gate.</strong> '
                          'Close this design as a hardness lead; no paid Astra follow-up is scheduled.')
        ending_note = (f'<h4>Broader 4D pilot: interactions between stems and endings</h4><p class="note">'
                       f'<strong>{ending["received"]}/96 responses received; {ending["settled"]}/96 settled.</strong> '
                       f'{score}<br>Execution: {escape(ending["execution"]["state"].replace("_"," "))}. '
                       '96 questions from 96 verbal families, all ten classes, six tense/mood categories and 25% aorist. '
                       'The public input remains dictionary dhātu plus the original four coordinates. '
                       'The four equally weighted grammar groups cover periphrastic-future endings, secondary plural clusters, '
                       'optative/benedictive plural endings, and a specific aorist ending interaction. '
                       'All questions use active voice; this is a targeted diagnostic, not uniform coverage of the whole Cartesian product.</p>'
                       '<p class="forward-copy">Independent review regenerated all 124 canonical forms and checked 172 additional '
                       'licensed spellings across 62 questions before execution. Canonical answers and raw responses remain preserved. '
                       '<strong>Difficulty is unproven:</strong> all 19 matching historical examples were correct. '
                       'Advancement requires below-90% accuracy after source review, at least 92 usable responses, '
                       'and supported errors spanning at least eight families, three classes and three grammar groups. '
                       'No interim score-based stopping, question replacement or automatic Astra follow-up.</p>'
                       f'<p class="forward-copy">Opus 5.5 xHigh, 65,536-token ceiling, eight concurrent calls and no paid retries. '
                       f'Settled cost: <strong>${ending["cost_upper_usd"]:.2f}</strong>; '
                       f'${ending["committed_usd"]:.2f} including outstanding maximum reservations. '
                       'The whole pilot reserves at most <strong>$126.41</strong> within the existing $1,000 Anthropic cap; '
                       '$166.84 remains protected for final evaluation. '
                       '<a href="parallel-search-20261007/four_d-90/ending-screen-01/plan.json">Frozen task plan</a> · '
                       f'<a href="parallel-search-20261007/four_d-90/ending-screen-01/{execution_link}">Execution</a> · '
                       '<a href="parallel-search-20261007/four_d-90/ending-screen-01/independent-source-review.md">Independent source review</a> · '
                       f'<a href="parallel-search-20261007/four_d-90/ending-screen-01/{analysis_link}">Live status and analysis</a>.</p>')
        if (ending_dir/'independent-result-review.md').exists():
            ending_note += ('<p class="forward-copy"><a href="parallel-search-20261007/four_d-90/'
                            'ending-screen-01/independent-result-review.md">Independent completed-result audit</a>.</p>')
    scheduling_path = runner.ROOT/'benchmarks/parallel-search-20261007/acceleration/scheduling-audit.md'
    if scheduling_path.exists():
        scheduling_note = ('<h4>Faster execution within the same caps</h4><p class="forward-copy">'
                           'The earlier 200-question comparison and 96-question pilot have completed. Their independent reviews ran in parallel. '
                           'Astra spent about 70 minutes in sequential ten-question groups; slow responses left other '
                           'slots idle. The new separately reviewed evaluator removes those group barriers and reserves the '
                           'full possible cost of every in-flight request before submission. Existing prompts, xHigh '
                           'reasoning and 65,536-token ceilings remain the comparison protocol. '
                           'Timing replays are conditional estimates; current deployment status appears in the paired-evaluation section. '
                           '<a href="parallel-search-20261007/acceleration/scheduling-audit.md">Measured bottleneck, timing replay and budget limits</a>.</p>')
    final = analysis.get('continuous_4d_final')
    if final:
        execution = final['execution']
        has_final_scores = bool(final.get('analysis') or final.get('infrastructure_analysis'))
        runtime_slots = execution.get('runtime_concurrency', final['plan']['concurrency'])
        execution_label = execution['state'].replace('_', ' ')
        scheduling_description = ('Sixteen requests per provider run continuously, refilling as responses finish, '
                                  'with xHigh and the same 65,536-token ceiling. ')
        if runtime_slots == {'Anthropic': 0, 'OpenAI': 32}:
            scheduling_description = ('Opus has finished. Astra uses up to 32 concurrent requests after a recorded '
                                      'handoff that waited for all previously admitted calls to settle. Requests '
                                      'continue from the next unanswered question with xHigh and the same '
                                      '65,536-token ceiling; budget reservations can reduce the active count. ')
        else:
            handoff = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-concurrency-32/drain-request.json'
            providers = execution.get('providers', {})
            if (handoff.exists() and execution['state'] in {'running', 'stopped_incomplete'}
                    and providers and not any(p.get('operational_failure') for p in providers.values())):
                pending = sum(p['admitted']-p['terminal_usage'] for p in providers.values())
                execution_label = 'draining for scheduling handoff' if pending else 'drained; continuation checkpoint pending'
                scheduling_description = ('New admissions are paused while previously admitted requests finish. '
                                          'The reviewed continuation can use up to 32 Astra workers after every '
                                          'outstanding request is settled and the exact saved position is checked. '
                                          'Model settings and spending limits remain fixed. ')
        failures = {provider: p['operational_failure']
                    for provider, p in execution.get('providers', {}).items()
                    if p.get('operational_failure')}
        if failures:
            execution_label = 'new submissions paused after a transport error'
            scheduling_description = ('The faster scheduler encountered a provider error and stopped admitting '
                                      'new requests while outstanding calls finish. Saved successful responses '
                                      'are retained, and the failed request keeps its full maximum cost reservation. '
                                      'Recovery is being reviewed before further submissions; no partial scores '
                                      'are used to choose the recovery or benchmark membership. ')
        carry = execution.get('acknowledged_transport_failures', [])
        if carry and execution['state'] in {
                'running_with_acknowledged_infrastructure_failure',
                'complete_attempted_pending_paired_analysis'}:
            execution_label = ('remaining questions running; one preserved gateway failure'
                               if execution['state'].startswith('running') else
                               'all questions attempted; one preserved gateway failure')
            scheduling_description = ('A separately recorded continuation evaluates the remaining questions with '
                                      'up to 31 concurrent Astra requests, preserving one failed request and its full '
                                      'cost reservation. That gateway failure is not replayed or counted as a '
                                      'demonstrated model error. The model settings, questions and caps are unchanged. ')
            if execution['state'] == 'complete_attempted_pending_paired_analysis':
                scheduling_description = ('The continuation has finished every remaining question using up to '
                                          '31 concurrent Astra requests. One earlier gateway failure remains '
                                          'explicitly missing, with its full cost reservation retained. '
                                          'The model settings, questions and caps are unchanged. ')
        result_status = ('The evaluation and receipt checks have finished; observed scores appear below. '
                         'Linguistic source adjudication remains in progress. ' if has_final_scores else
                         'Scores wait until the declared evaluation and receipt checks finish. Completion depends on actual usage '
                         'fitting the caps; budget or operational failures leave an explicitly incomplete cohort. ')
        rows = ''
        for provider, label in [('Anthropic','Opus 5.5'),('OpenAI','GPT-6 Astra')]:
            p = execution.get('providers',{}).get(provider,{})
            rows += (f'<tr><td>{label}</td><td>{p.get("admitted",0):,}/1,800</td>'
                     f'<td>{p.get("terminal_usage",0):,}/1,800</td>'
                     f'<td>${p.get("settled_cost_usd",0):.2f}</td>'
                     f'<td>${p.get("committed_usd",0):.2f}</td></tr>')
        continuous_note = (f'<h4>1,800-question paired evaluation</h4><p class="note">'
                           f'<strong>{escape(execution_label)}.</strong> '
                           'The complete cohort uses original dictionary dhātu plus four coordinates. '
                           f'{scheduling_description}The limits for this run are $100 Anthropic and $225 OpenAI, '
                           'inside the existing lifetime caps and protected reserves.</p>'
                           '<div class="table-scroll"><table><thead><tr><th>Reference</th><th>Submitted</th>'
                           '<th>Usage settled</th><th>Known spend</th><th>Spend + outstanding maxima</th></tr></thead>'
                           f'<tbody>{rows}</tbody></table></div><p class="forward-copy">'
                           f'{result_status}Item-level and family-based uncertainty are reported separately, and every unrecognized usable '
                           'answer still requires independent source adjudication. '
                           '<a href="parallel-search-20261007/four_d-90/final1800-64k-01/README.md">Current evaluation and artifact guide</a> · '
                           '<a href="parallel-search-20261007/four_d-90/final1800-64k-01/execution-plan.json">Fixed execution plan</a> · '
                           '<a href="parallel-search-20261007/acceleration/continuous64k-code-review-01.md">Independent evaluator review</a>.</p>')
        if execution.get('scheduling_amendment_sha256'):
            continuous_note += ('<p class="forward-copy"><a href="parallel-search-20261007/four_d-90/'
                                'final1800-64k-01/astra-concurrency-32/README.md">Recorded Astra scheduling amendment</a>. '
                                'The 1,800-question membership, provider settings and total spending limits remain '
                                'those of the original evaluation.</p>')
        if final.get('analysis'):
            continuous_note += completed_final_tables(final['analysis'])
        if carry:
            continuous_note += ('<p class="forward-copy"><a href="parallel-search-20261007/four_d-90/'
                                'final1800-64k-01/astra-infrastructure-carry-01/README.md">'
                                'Infrastructure continuation and missing-answer policy</a>. '
                                'The separate analysis requires all 1,800 questions to have been attempted '
                                'and every request other than the recorded gateway failure to have settled. '
                                'It preserves the full denominator and reports the missing-answer bounds.</p>')
            reviewed_analysis = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/analysis-adoption.json'
            if reviewed_analysis.exists():
                continuous_note += ('<p class="forward-copy">The separate analysis procedure and independent answer '
                                    'checker preserve all received answers and the recorded infrastructure failure. '
                                    'Both missing-answer possibilities are included in the '
                                    'accuracy and precision calculations. '
                                    '<a href="parallel-search-20261007/four_d-90/final1800-64k-01/'
                                    'astra-infrastructure-carry-01/analysis-review.json">Analysis review</a> · '
                                    '<a href="parallel-search-20261007/four_d-90/final1800-64k-01/'
                                    'astra-infrastructure-carry-01/independent-review/README.md">Independent answer checker</a>.</p>')
        if final.get('infrastructure_analysis'):
            continuous_note += attempted_final_tables(final['infrastructure_analysis'])
            continuous_note += source_audit_followup()
            review_path = runner.ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/independent-review/completed-review/review.json'
            if review_path.exists():
                review = io.read_json(review_path)
                if (review.get('passed') and review.get('primary_analysis_sha256') == io.sha256(
                        review_path.parents[2]/'analysis.json')):
                    continuous_note += ('<p class="note"><strong>Independent grading check passed.</strong> '
                                        'The second checker reproduced all 3,599 received-response grades with zero '
                                        'disagreements and preserved the missing Astra response. '
                                        'It also checked question identities, prompt isolation, costs and analytic standard errors. '
                                        'Linguistic source adjudication is now in progress; this mechanical check does not '
                                        'certify every accepted or rejected Sanskrit form. '
                                        '<a href="parallel-search-20261007/four_d-90/final1800-64k-01/'
                                        'astra-infrastructure-carry-01/independent-review/completed-review/review.json">'
                                        'Completed independent check</a>.</p>')
    larger_path = scale_path.parent/'candidate-1800-v1/manifest.json'
    if larger_path.exists():
        larger = io.read_json(larger_path)
        prefix = 'parallel-search-20261007/four_d-90/candidate-1800-v1'
        larger_note = (f'<h4>Latest candidate: 1,800 questions</h4><p class="note">'
                       f'<strong>{larger["n"]:,} questions across {larger["families"]} verbal families.</strong> '
                       'All 1,250 previous questions are retained unchanged, with 550 added using input-only selection. '
                       'The composition is 936 short-adanta non-aorist, 144 other-adanta aorist and 720 broader controls. '
                       'All ten classes and tenses are represented, aorist remains 12%, and each person and number has '
                       'exactly 600 questions. Active voice is fixed and 60% of questions are class 10.</p>'
                       '<p class="forward-copy">At the development rates, projected independent-question SE is '
                       '<strong>0.78 pp for Opus and 0.93 pp for Astra</strong>. The difficult 52% component still '
                       'uses only 14 test families; below-one-point precision for generalization to new verbal families '
                       'remains unproven. All 220 additional broad families are class 1 (Bhvadi); the other nine classes '
                       'retain their previous representation. Qualification requires the paired evaluation and subsequent source adjudication. '
                       f'<a href="{prefix}/README.md">Composition and limitations</a> · '
                       f'<a href="{prefix}/public-prompts.json">All 1,800 public questions</a> · '
                       f'<a href="{prefix}/manifest.json">Manifest</a>.</p>')
        if (larger_path.parent/'scoring-adoption.json').exists():
            larger_note += ('<p class="forward-copy"><strong>Independent input and spelling reviews passed.</strong> '
                            'All 1,800 forms regenerate; input history and the strict training inventory are disjoint. '
                            'The prospective scoring policy preserves 3,224 canonical forms and 3,289 finite alternatives '
                            'across 1,193 questions. Every usable unrecognized answer will still receive source adjudication; '
                            '79 questions have explicit residual spelling flags. '
                            f'<a href="{prefix}/independent-input-review.json">Input review</a> · '
                            f'<a href="{prefix}/scoring-adoption.json">Scoring declaration</a> · '
                            f'<a href="{prefix}/spelling-policy-proposal/independent-review.json">Independent spelling review</a>.</p>')
        precision_path = larger_path.parent.parent/'precision-design-audit/audit.json'
        if precision_path.exists():
            precision = io.read_json(precision_path)
            opus_se = 100*precision['models']['Opus']['fixed_three_cell_family_bootstrap']['se']
            astra_se = 100*precision['models']['Astra']['fixed_three_cell_family_bootstrap']['se']
            larger_note += ('<p class="forward-copy"><strong>Precision sensitivity:</strong> holding the 52/8/40 '
                            'mixture fixed while resampling verbal families within each component gives development SE '
                            f'{opus_se:.2f} pp for Opus and {astra_se:.2f} pp for Astra. This modestly reduces the earlier '
                            'family estimates but does not establish sub-one-point precision. Uncertainty on new roots, '
                            'new coordinates within fixed roots, and repeated runs of the same questions are different '
                            'quantities; the original “stddev &lt;1%” request does not specify which one. The frozen '
                            'evaluation still reports both item and family uncertainty. '
                            '<a href="parallel-search-20261007/four_d-90/precision-design-audit/README.md">Methods and interpretation</a>.</p>')
        repeat_note = larger_path.parent.parent/'repeat-sd-note/independent-review.json'
        if repeat_note.exists() and io.read_json(repeat_note).get('passed'):
            larger_note += ('<details><summary>What 1,800 questions can say about repeat-run stability</summary>'
                            '<p class="forward-copy">A separate, independently reviewed calculation concerns repeating '
                            'the same fixed questions. Under independent calls, stable per-question probabilities and '
                            'a fixed scorer, at least 1,434 known-correct answers out of 1,800 would give an upper '
                            'confidence bound below one percentage point for that model’s repeat-run SD. The two '
                            'prespecified references receive at least 95% joint repeated-experiment coverage. '
                            'This threshold was established before final scores were inspected; it is not an empirical rerun measurement. '
                            'It does not cover shared provider drift, correlated outages, or generalization to new roots; '
                            'the existing family-precision requirement remains unchanged. '
                            '<a href="parallel-search-20261007/four_d-90/repeat-sd-note/README.md">Derivation and assumptions</a> · '
                            '<a href="parallel-search-20261007/four_d-90/repeat-sd-note/independent-review.md">Independent mathematical review</a>.</p></details>')
            application_path = repeat_note.parent/'completed-result-application.json'
            if application_path.exists():
                application = io.read_json(application_path)
                if application.get('independent_formula_crosscheck_passed'):
                    a = application['results']
                    larger_note += ('<p class="forward-copy"><strong>Applied to the completed canonical scores:</strong> '
                                    f'the conditional repeat-SD upper bounds are {100*a["Anthropic"]["fixed_panel_repeat_sd_upper"]:.2f} pp '
                                    f'for Opus and {100*a["OpenAI"]["fixed_panel_repeat_sd_upper"]:.2f} pp for Astra. '
                                    'These are mathematical bounds under the assumptions above, with zero empirical reruns. '
                                    'They do not certify revised source scoring or remove the family-precision limitation. '
                                    '<a href="parallel-search-20261007/four_d-90/repeat-sd-note/completed-result-application.json">'
                                    'Completed-count calculation</a>.</p>')
        source_pack = larger_path.parent.parent/'final1800-source-pack'
        if (source_pack/'source-adjudication-adoption-02.json').exists():
            larger_note += ('<p class="forward-copy"><strong>Source follow-up before inspecting answers:</strong> '
                            'independent review supports 19 exact additional forms for कथ and गण: two printed '
                            'examples plus 17 forms established from the licensed stems and ordinary present/imperative '
                            'rules. These additions apply consistently to both models in a separate source-adjudicated '
                            'score. The original questions, canonical keys and predeclared spelling scores are preserved. '
                            'Other roots and unlisted paradigms still require review. The source reference pack maps '
                            'all 35 hard-component families and 1,080 questions. '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/README.md">Source reference pack</a> · '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/source-adjudication-adoption-02.json">Exact supplemental acceptance</a> · '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/puk-extension-supplement/independent-review.md">Independent derivation review</a>.</p>')
        elif (source_pack/'source-adjudication-adoption-01.json').exists():
            larger_note += ('<p class="forward-copy"><strong>Source follow-up before inspecting answers:</strong> '
                            'independent review supports two additional printed forms, कथापयति and गणापयति, '
                            'for their exact present third-person singular questions. These will be accepted consistently '
                            'for both models in a separate source-adjudicated score, preserving the original canonical '
                            'and predeclared spelling scores. Broader paradigms remain subject to review. '
                            'A source reference pack now maps all 35 hard-component families and 1,080 questions. '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/README.md">Source reference pack</a> · '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/source-adjudication-adoption-01.json">Exact supplemental acceptance</a> · '
                            '<a href="parallel-search-20261007/four_d-90/final1800-source-pack/independent-puk-review.md">Independent source review</a>.</p>')
    if fast and fast['execution']['state'] == 'complete':
        reviews = ('<p class="forward-copy"><strong>Independent result review:</strong> all 25 creation misses and 19 matched successes were inspected, '
                   'and all 200 creation keys and scores were reproduced. No demonstrated key or scoring error required a correction; '
                   'this bounded review does not certify every possible licensed variant. The modification review checked all 400 paired responses '
                   'and actual API requests, confirming the scores and absence of hidden dhātu or answer leakage. '
                   '<a href="parallel-search-20261007/four_d-90/direct-result-source-review.md">4D source review</a> · '
                   '<a href="parallel-search-20261007/modification-01/direct-result-review.md">Modification audit</a>.</p>')
    budget_note = 'The three new batches reserve at most <strong>$395.02 combined</strong>. Existing protected evaluation reserves remain intact.'
    if fast:
        originals = [state['jobs'].get(name, {}) for name in
                     ['opus-simple4d-90-01', 'opus-modification-01', 'opus-modification-control-01']]
        original_note = ('All three original batches have ended and their billing is reconciled; no original-batch reservation remains. '
                         if all(j.get('settled') for j in originals) else
                         'Original batches retain their full cost reservations until billing is reconciled. ')
        fast_note = (f'<p class="note"><strong>Direct execution: {received}/600 responses received; '
                     f'{fast["settled_requests"]}/600 settled.</strong> Eight concurrent requests, unchanged model, '
                     'prompts and token ceiling. Full direct panels are the primary evaluation; original batch outcomes stay separate. '
                     f'Executor: {escape(fast["execution"]["state"].replace("_"," "))}.</p>')
        budget_note = (f'Direct execution is limited to <strong>$100 additional Anthropic spend</strong>, with a maximum '
                       f'$52.67 reservation per 40-question group. Actual direct cost settled so far: '
                       f'<strong>${fast["settled_cost_usd"]:.2f}</strong>. The unused Anthropic sensitivity reserve was reassigned; '
                       f'${runner.protected_remaining(state,"Anthropic")/1e6:.2f} remains reserved for final evaluation. '
                       + original_note +
                       '<a href="parallel-search-20261007/acceleration/plan.json">Frozen acceleration plan</a>.')
    current_lead = ''
    diversity_note = ''
    diversity_path = runner.ROOT/'benchmarks/visualizations/vp-bench-diversity.html'
    if diversity_path.exists():
        diversity_note = ('<details id="vp-diversity-explorer" open><summary>Explore dhātu and four-coordinate diversity</summary>'
                          '<style>#vp-diversity-1800{--foreground:var(--ink);--muted-foreground:var(--muted);'
                          '--border:var(--line);--viz-series-1:var(--teal);--viz-series-2:var(--orange);'
                          '--viz-series-3:var(--blue);margin:18px 0 24px}'
                          '#vp-diversity-1800 .text-small{font-size:13px}'
                          '#vp-diversity-1800 select{width:100%;padding:8px;border:1px solid var(--line);'
                          'background:var(--white);color:var(--ink)}</style>'
                          + diversity_path.read_text() +
                          '<p class="forward-copy">The 90-cell view is the selected active-voice reference grid '
                          '(10 tense/mood values × 3 persons × 3 numbers). An empty cell means no question was selected; '
                          'it does not assert that the form is ungrammatical. Coverage of all 90 cells across the '
                          'whole benchmark does not imply all 90 were tested for each dhātu. '
                          'Dictionary entries are distinguished by citation and class; some share a written citation. '
                          '<a href="analysis/vp-bench-diversity.json">Exact summary statistics and per-root coverage</a>.</p></details>')
    if final and final.get('infrastructure_analysis'):
        current_lead = ('<p class="note"><strong>The 1,800-question original-4D evaluation has finished.</strong> '
                        'Both references initially score below 90%; source review is checking valid alternatives '
                        'and dictionary defects. Coverage spans 755 families and ten tenses, with 12% aorist. '
                        'Difficulty is concentrated in a few families, and the new-family precision requirement '
                        'remains unmet. <a href="#current-1800-evaluation">Current results and source audit</a>.</p>')
        continuous_note = '<div id="current-1800-evaluation">' + continuous_note + '</div>'
    return f'''<article id="simple-search-summary" class="panel panel-pad" aria-labelledby="simple-search-title" style="margin-bottom:28px">
<span class="eyebrow">Current investigation · 7 October 2026</span>
<h3 id="simple-search-title">One VP-Bench. Prefer the original four coordinates.</h3>
<p class="forward-copy">The goal is a simple conjugation benchmark with strongest-model accuracy below 90%, ideally with enough headroom to improve through post-training. The earlier two-benchmark and exact 79–81% targets are superseded. The current candidate uses ordinary dhātu plus four coordinates. The completed alternative pilot used word modification; <strong>the modification prompt contains no dhātu</strong>.</p>
{current_lead}
{diversity_note}
{fast_note}
<div class="table-scroll"><table><thead><tr><th>Frozen development panel</th><th>Composition</th><th>Opus 5.5</th></tr></thead><tbody>
<tr><td>4D creation challenge<br><span class="small">Dhātu + tense/mood × voice × person × number</span></td><td>200 questions · 109 families · all 10 classes and tenses · 12% aorist</td><td>{result('four_d')}</td></tr>
<tr><td>Modification without dhātu<br><span class="small">Source word + source coordinates + target coordinates</span></td><td>200 questions · 200 families · all 10 classes and target tenses · 10% target aorist</td><td>{result('modification')}</td></tr>
<tr><td>Matched 4D creation control</td><td>Same 200 target forms and full accepted answer sets as modification</td><td>{result('modification', 'control')}</td></tr>
</tbody></table></div>
<p class="forward-copy">{comparison}</p>
{source_note}
{findings}
{reviews}
{astra_note}
{ending_note}
{continuous_note}
{scheduling_note}
{scale_note}
{larger_note}
{training_note}
<div class="two-col"><div><h4>What makes the 4D set a challenge?</h4><p class="forward-copy">104 questions cover short-penultimate adanta class-10 verbs outside the aorist; 16 cover other adanta aorists; 80 provide broader controls. This is a grammar-defined mixture selected from earlier development evidence. It has <strong>60% class-10 verbs</strong>. The difficult non-aorist component has only 13 development families and 14 reserved test families, so a low score alone would not establish the desired diversity or precision.</p></div>
<div><h4>What does modification test?</h4><p class="forward-copy">Only tense/mood changes; voice, person and number stay fixed. Sources are present, perfect, imperfect and aorist, 50 each. Each source word and coordinate tuple identifies one family in the audited dictionary. A shadow check across all 2,229 entries blocks collisions with excluded entries. Uniqueness is bounded to this dictionary and its canonical engine forms. Both pilot designs currently use active voice only.</p></div></div>
<p class="note warm"><strong>Development evidence, not a released benchmark.</strong> Both references use xHigh, a 65,536 output-token ceiling, one answer, no tools or paid retries. Full panels were frozen before submission. Modification and controls use Sanskrit instructions; the separate 4D challenge uses the existing English prompt. Qualification still requires a frozen independent test set, completed source adjudication and sufficient family diversity. Final size remains at least 500, preferably 1,000+, with sampling standard error below one percentage point; these 200-question pilots do not establish that precision. At the observed rates, even independent questions require at least 1,094 for Opus and 1,570 for Astra; related forms may require more.</p>
<p class="forward-copy">{'<br>'.join(budgets)}.<br>{budget_note}</p>
<details><summary>Batch state and reproducible inputs</summary><ul>{''.join(jobs)}</ul><p class="small">Snapshot: {escape(analysis['updated_at'])}. Collector refreshes this page on disk; reload to see updates.</p>
<p><a href="parallel-search-20261007/plan.json">Current plan</a> · <a href="parallel-search-20261007/coordinator-registration.json">Frozen registration</a> · <a href="{analysis_path}">Full analysis</a> · <a href="parallel-search-20261007/four_d-90/handoff.md">4D composition</a> · <a href="parallel-search-20261007/modification-01/README.md">Modification design</a></p></details>
</article>'''
