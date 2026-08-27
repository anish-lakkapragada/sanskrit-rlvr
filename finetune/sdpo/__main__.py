from finetune.sdpo.train import main

# Guard is REQUIRED: vLLM v1 starts its EngineCore with the multiprocessing
# 'spawn' method, which re-imports __main__ in the child — without the guard
# the child would re-run the whole trainer (and crash on the spawn check).
if __name__ == "__main__":
    main()
