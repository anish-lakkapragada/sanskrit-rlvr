use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::{self, BufRead};
use vidyut_prakriya::args::*;
use vidyut_prakriya::Vyakarana;

#[derive(Deserialize)]
struct Request {
    code: String,
    dhatu: String,
    gana: Gana,
    antargana: Option<Antargana>,
    unadi: Option<Unadi>,
}

fn main() {
    let v = Vyakarana::new();
    for line in io::stdin().lock().lines() {
        let r: Request = serde_json::from_str(&line.unwrap()).unwrap();
        let text = Slp1String::from(r.dhatu).unwrap();
        let dhatu = if let Some(a) = r.antargana {
            Dhatu::mula_with_antargana(text, r.gana, a)
        } else {
            Dhatu::mula(text, r.gana)
        };
        let mut rows = Vec::new();
        for suffix in Unadi::iter().filter(|s| r.unadi.map_or(true, |chosen| *s == chosen)) {
            let derivations = v.derive_krdantas(&Krdanta::new(dhatu.clone(), suffix));
            let stems: BTreeSet<_> = derivations.iter().map(|p| p.text()).collect();
            if !stems.is_empty() {
                let rules: BTreeSet<_> = derivations.iter().flat_map(|p| p.history().iter().map(|h| format!("{:?}", h.rule()))).collect();
                rows.push(serde_json::json!({"suffix": suffix, "aupadeshika": suffix.as_str(), "visible": suffix.drshya(), "stems": stems, "rules": rules}));
            }
        }
        println!("{}", serde_json::json!({"code":r.code,"candidates":rows}));
    }
}
