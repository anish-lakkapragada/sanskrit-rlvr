-- The forced/free map of the Śivasūtra ordering (Lean 4).
import Panini.Basic        -- the model: sounds, markers, the 14 Śivasūtras, pratyāhāra
import Panini.Pratyahara   -- lax and strict pratyāhāra semantics
import Panini.Interval     -- infrastructure (duplication obstruction)
import Panini.Markers      -- infrastructure (right-edge rigidity)
import Panini.Optimality   -- infrastructure here: defines the 43 attested classes
import Panini.Necessity    -- infrastructure here: the single-witness refutation lemma
import Panini.Ordering     -- THE RESULT: 11 forced / 18 free adjacent transpositions
