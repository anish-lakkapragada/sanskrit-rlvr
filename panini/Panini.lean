-- Pāṇini's Śivasūtras in Lean 4 — the build path from the `thinking/` notes.
import Panini.Basic        -- the model: sounds, markers, the 14 Śivasūtras, pratyāhāra
import Panini.Pratyahara   -- Rung ①: the abbreviations denote what the tradition says
import Panini.Interval     -- route (b) engine, Moves 1–2: encoding = interval; independence forces duplication
import Panini.Markers      -- route (b) Move 3: markers are right-endpoints; antichains force markers
import Panini.Optimality   -- Rung ②: the ordering is an optimal S-alphabet (Petersen 2004)
