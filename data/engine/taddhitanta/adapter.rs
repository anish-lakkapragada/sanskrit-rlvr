//! Gender-aware bridge for resolved, single-term nominal inputs.
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::io;
use std::panic::{catch_unwind, AssertUnwindSafe};
use vidyut_prakriya::args::{Linga, Pratipadika, Slp1String, Taddhita, TaddhitaArtha, Taddhitanta};
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
    gender: Linga,
    suffix: Taddhita,
    artha: Option<TaddhitaArtha>,
}

#[derive(Serialize)]
struct EngineError {
    r#type: String,
    message: String,
}

#[derive(Serialize)]
struct Response {
    id: String,
    forms: BTreeSet<String>,
    resulting_meanings: BTreeSet<String>,
    error: Option<EngineError>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let batch: Batch = serde_json::from_reader(io::stdin().lock())?;
    let mut engine = Vyakarana::builder()
        .log_steps(batch.log_steps)
        .is_chandasi(false)
        .use_svaras(false)
        .nlp_mode(false)
        .build();
    let mut responses = Vec::new();
    for request in batch.requests {
        // Invalid adapter input aborts the batch; it must never become an empty derivation.
        if request.is_nyap && request.gender != Linga::Stri {
            return Err("nyap requires feminine source gender".into());
        }
        let text = Slp1String::from(&request.stem)?;
        let stem = if request.is_nyap { Pratipadika::nyap(text) } else { Pratipadika::basic(text) };
        let mut builder = Taddhitanta::builder();
        builder.pratipadika(stem).taddhita(request.suffix);
        if let Some(artha) = request.artha { builder.artha(artha); }
        let args = builder.build()?.with_stem_linga(request.gender);
        let mut response = Response {
            id: request.id, forms: BTreeSet::new(), resulting_meanings: BTreeSet::new(), error: None,
        };
        match catch_unwind(AssertUnwindSafe(|| engine.derive_taddhitantas(&args))) {
            Ok(derived) => {
                response.forms = derived.iter().map(|p| p.text()).collect();
                response.resulting_meanings = derived.iter().map(|p| format!("{:?}", p.artha())).collect();
            }
            Err(payload) => {
                let message = payload.downcast_ref::<String>().cloned()
                    .or_else(|| payload.downcast_ref::<&str>().map(|s| s.to_string()))
                    .unwrap_or_else(|| "unknown engine panic".to_string());
                response.error = Some(EngineError { r#type: "EnginePanic".into(), message });
                engine = Vyakarana::builder().log_steps(batch.log_steps)
                    .is_chandasi(false).use_svaras(false).nlp_mode(false).build();
            }
        }
        responses.push(response);
    }
    serde_json::to_writer(io::stdout().lock(), &responses)?;
    Ok(())
}
