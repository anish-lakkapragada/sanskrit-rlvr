use vidyut_prakriya::args::*;
use vidyut_prakriya::Vyakarana;
use std::io::{self,BufRead};
use serde::Deserialize;
#[derive(Deserialize)]
struct Item { stem: Option<String>, dhatu: Option<String>, gana: Option<Gana>, antargana: Option<Antargana>, sanadi: Option<Vec<Sanadi>>, prefixes: Option<Vec<String>>, krt: Option<BaseKrt> }
#[derive(Deserialize)]
struct Request { mode:Option<String>, items:Vec<Item>, samasa_type:SamasaType, vibhakti:Vibhakti, vacana:Vacana }
fn main() {
 let v=Vyakarana::new();
 for line in io::stdin().lock().lines() {
  let line=line.unwrap(); let r:Request=serde_json::from_str(&line).unwrap();
  let mut padas=Vec::new(); let mut members=Vec::new();
  for item in r.items {
   let stem=if let Some(s)=item.stem {Pratipadika::basic(Slp1String::from(s).unwrap())} else {
    let text=Slp1String::from(item.dhatu.unwrap()).unwrap(); let gana=item.gana.unwrap();
    let mula=if let Some(a)=item.antargana {Dhatu::mula_with_antargana(text,gana,a)} else {Dhatu::mula(text,gana)};
    let dhatu=mula.with_sanadi(&item.sanadi.unwrap_or_default()).with_prefixes(&item.prefixes.unwrap_or_default());
    let k=Krdanta::new(dhatu,item.krt.unwrap());
    let derived=v.derive_krdantas(&k);
    let stems:std::collections::BTreeSet<_>=derived.iter().map(|p|p.text()).collect();
    let rules:std::collections::BTreeSet<_>=derived.iter().flat_map(|p|p.history().iter().map(|h|format!("{:?}",h.rule()))).collect();
    members.push(serde_json::json!({"stems":stems,"rules":rules})); Pratipadika::from(k)
   };
   padas.push(Subanta::new(stem,Linga::Pum,r.vibhakti,Vacana::Eka));
  }
  if r.mode.as_deref()==Some("members") {println!("{}",serde_json::json!({"members":members}));continue;}
  let samasa=Samasa::builder().padas(padas).samasa_type(r.samasa_type).build().unwrap();
  let compound_stems:Vec<_>=v.derive_samasas(&samasa).iter().map(|p|p.text()).collect();
  let output=v.derive_subantas(&Subanta::new(Pratipadika::from(samasa),Linga::Pum,r.vibhakti,r.vacana));
  let forms:std::collections::BTreeSet<_>=output.iter().map(|p|p.text()).collect();
  println!("{}",serde_json::json!({"stems":compound_stems,"forms":forms,"members":members}));
 }
}
