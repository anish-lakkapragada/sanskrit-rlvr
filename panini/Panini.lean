-- Pāṇini's Śivasūtras in Lean 4: the optimality theorem (Petersen 2004/2008).
import Panini.Basic        -- the model: sounds, markers, the 14 Śivasūtras, pratyāhāra
import Panini.Pratyahara   -- the abbreviations denote what the tradition says; strict semantics
import Panini.Interval     -- Moves 1–2: encoding = interval; independence forces duplication
import Panini.Markers      -- Move 3: markers are right-endpoints; antichains force markers
import Panini.Optimality   -- the ordering is an optimal S-alphabet
