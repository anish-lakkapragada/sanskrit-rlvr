use serde::Deserialize;
use std::collections::BTreeSet;
use std::io::{self, BufRead};
use vidyut_prakriya::args::*;
use vidyut_prakriya::Vyakarana;

#[derive(Deserialize)]
struct Request { stem:String, lakara:Lakara, purusha:Purusha, vacana:Vacana }
fn main() {
    let v = Vyakarana::new();
    for line in io::stdin().lock().lines() {
        let r:Request = serde_json::from_str(&line.unwrap()).unwrap();
        let noun = Pratipadika::basic(Slp1String::from(r.stem).unwrap());
        let dhatu = Dhatu::nama(noun, Some(Sanadi::kyac));
        let args = Tinanta::builder().dhatu(dhatu).prayoga(Prayoga::Kartari)
            .pada(DhatuPada::Parasmaipada).lakara(r.lakara)
            .purusha(r.purusha).vacana(r.vacana).build().unwrap();
        let ps = v.derive_tinantas(&args);
        let forms:BTreeSet<_> = ps.iter().map(|p|p.text()).collect();
        let rules:BTreeSet<_> = ps.iter().flat_map(|p|p.history().iter().map(|h|format!("{:?}",h.rule()))).collect();
        println!("{}",serde_json::json!({"forms":forms,"rules":rules}));
    }
}
