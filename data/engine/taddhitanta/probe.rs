//! Small JSON bridge to the Rust engine shipped in Python vidyut 0.4.0.
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::io;
use vidyut_prakriya::args::{Pratipadika, Slp1String, Taddhita, TaddhitaArtha, Taddhitanta};
use vidyut_prakriya::Vyakarana;

#[derive(Deserialize)]
struct Batch {
    log_steps: bool,
    requests: Vec<Request>,
}

#[derive(Deserialize)]
struct Request {
    id: String,
    stem: String,
    is_nyap: bool,
    suffix: Taddhita,
    artha: Option<TaddhitaArtha>,
}

#[derive(Serialize)]
struct Response {
    id: String,
    forms: BTreeSet<String>,
    resulting_meanings: BTreeSet<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let batch: Batch = serde_json::from_reader(io::stdin().lock())?;
    let engine = Vyakarana::builder()
        .log_steps(batch.log_steps)
        .is_chandasi(false)
        .use_svaras(false)
        .nlp_mode(false)
        .build();
    let mut responses = Vec::new();
    for request in batch.requests {
        let text = Slp1String::from(&request.stem)?;
        let stem = if request.is_nyap {
            Pratipadika::nyap(text)
        } else {
            Pratipadika::basic(text)
        };
        let mut builder = Taddhitanta::builder();
        builder.pratipadika(stem).taddhita(request.suffix);
        if let Some(artha) = request.artha {
            builder.artha(artha);
        }
        let args = builder.build()?;
        let derived = engine.derive_taddhitantas(&args);
        responses.push(Response {
            id: request.id,
            forms: derived.iter().map(|p| p.text()).collect(),
            resulting_meanings: derived.iter().map(|p| format!("{:?}", p.artha())).collect(),
        });
    }
    serde_json::to_writer(io::stdout().lock(), &responses)?;
    Ok(())
}
