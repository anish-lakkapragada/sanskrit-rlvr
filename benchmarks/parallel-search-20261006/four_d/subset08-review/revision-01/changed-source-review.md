# Bounded review of five changed recipe-rule contexts

**One concrete source-condition failure warrants holding revision01 before evaluation.** The remaining three unique rules match their visible trace contexts in this bounded check. This reviews the five contexts added relative to original08, not an exhaustive grammar audit.

## Desiderative plus 7.4.7: unsupported caṅ-conditioned branch

The [Kāśikā and Nyāsa on 7.4.7](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.7.htm) condition the optional retention/replacement of penultimate ṛ on ṇi before caṅ. Nyāsa explicitly illustrates Curādi kṝt with acīkṛtat, alongside the strengthening alternative. This is an exception to the ordinary vowel operations in that caṅ environment, not a general permission whenever the final tense happens to be Lun. [3.1.48](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.48.htm) assigns caṅ after the specified ṇi-ending stem in active aorists.

Exact revised question `cart5-95a72032f74081e76f462424` is Curādi 10.0351 tṛp, recipe `[san]`, active third-person plural Lun. The engine accepts ordinary-strengthened atitarpayiṣiṣata/atitarpayiṣiṣuḥ and also atitṛpayiṣiṣata/atitṛpayiṣiṣuḥ. Its latter derivations apply 7.4.7 first to the internal `[tṛp, Ric]`, before san insertion; again during desiderative construction; and again after the aorist ending is present. The aorist marker is **sic**, never caṅ. Thus the qualifying caṅ context for the extra ṛ branch is absent. The optional-Ric-free atitarpiṣiṣuḥ branch is a separate branch and is not evidence for the ṛ forms.

[The complete five-question traces](changed-source-controls.json) preserve each derivation. [Twelve ordinary/desiderative controls](rule747-positive-negative-controls.json) compare Lat, Lun and Lrt for 10.0351 and 10.0155. Desiderative non-aorist stems consistently use titarpayiṣ-/cikīrtayiṣ-; only Lun introduces the extra titṛpayiṣ-/cikṛtayiṣ- variants. Ordinary Curādi aorists correctly contain caṅ and retain the source-supported optional ṛ branch. The ordinary controls must therefore remain eligible under any new predicate. The read-only reproduction command `.venv/bin/python -m misc.vp_4d_rule747_controls` reproduced all twelve saved derivations exactly and checked caṅ presence versus absence.

The coordinator adopted the following conservative quarantine in policy21 after independently reading the primary source and reproducing the trace:

```python
task.get('derivation', {}).get('sanadi') == ['san'] and \
    '7.4.7' in task['campaign']['trace_rule_ids']
```

All current matches are Lun, but no handpicked lexical list is needed. This holds the uncertified accepted union, including cases where a redundant erroneous rule might leave an independently valid surface form; it does not declare every accepted form wrong. Preserve ordinary 4D, ordinary Ric, and san without this trace. Do not patch gold or select by model correctness.

[Input-only inventory](rule747-input-inventory.json): revision01 parent one/subset one; original08 zero; candidate04 inputs two; previously evaluated development pilot06 one and pilot07 chunk A three; cap60 zero. The earlier development entries include different lexical roots, supporting a rule-context predicate rather than an individual-question exception. This review read no model answers, so correct/wrong symmetry counts are left to the coordinator's uniform analyzer.

## Three rules with matching trace conditions

- **7.4.52, san/Lut, Bhvādi sah 01.0988.** The trace changes tā́s to tāh immediately before the first-person singular middle ending e. This directly matches the [Kāśikā condition and Nyāsa's periphrastic-future example](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.52.htm). The desiderative is already formed; no lexical or semantic extension is required.
- **8.3.78, san/Lit, Curādi svarta 10.0116.** Retroflexion occurs in the kṛ auxiliary's cakṛ+dhve junction, yielding the source's cakṛḍhve pattern inside the periphrastic perfect. [Kāśikā and Laghusiddhāntakaumudī](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.78.htm) explicitly give this auxiliary junction. The other auxiliaries remain in the accepted union. This is not a lexical operation on svarta.
- **8.4.64, two intensive recipes in passive forms, 01.0766 śucy and 01.0591 cucy.** Both traces have consonant+y+y at the base/passive-suffix junction and optionally delete the first y, preserving both single-y and double-y outputs. That matches [Kāśikā's hal+yam+yam optional-deletion condition and y examples](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.4.64.htm). The host page has inconsistent 8.4.63/64 headings; its rule text is unambiguous. No obligatory-deletion claim is made.

There is no concrete new blocker in these latter contexts. This limited conclusion does not certify every earlier stem operation or every possible accepted variant.
